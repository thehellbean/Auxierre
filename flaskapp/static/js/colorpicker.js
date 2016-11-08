var ColorPicker = {
	init: function(params){
		this.container = $(params["container"]);
		this.width = this.container.width();
		this.size = params["size"] || 20;
		this.indexWidth = this.width / this.size;
		this.height = params["height"] || this.indexWidth;

		this.container.append("<svg width="+this.width+" height="+this.height+"></svg>");
		this.svg = $(params["container"] + "> svg");
		
		this.cursorIndex = this.size / 2 - 1;
		this.selectedIndices = [this.cursorIndex];
		this.cursorPos = this.cursorIndex * this.indexWidth + this.indexWidth / 2;
		this.indicators = d3.select(params["container"]).append("svg").attr("width", this.width).attr("height", this.height / 2);
		this.setUpListeners();

		this.jsvg = this.svg;
		this.svg = d3.select(this.svg.selector);

		this.mouseHeld = false;

		this.default_colors = ["#392800", "none", "none", "#754800", "none", "none", "#007400", "none", "none", "#00d700", "#00d700", "none", "none", "#d16600", "none", "none", "#d33100", "none", "none", "#ff0000"];

		var iWidth = this.indexWidth;

		this.indicators.selectAll("rect").data(this.default_colors)
			.enter().append("rect")
			.attr("fill", function(d) { return d; })
			.attr("width", this.indexWidth / 2)
			.attr("x", function(d, i) { return i * iWidth + iWidth / 4; })
			.attr("height", this.height / 2);

		this.assignedColors = ["#392800", "none", "none", "#754800", "none", "none", "#007400", "none", "none", "#00d700", "#00d700", "none", "none", "#d16600", "none", "none", "#d33100", "none", "none", "#ff0000"];

		var size = this.size;

		var def = this.svg.append("defs");

		var gradient = def.data(this.default_colors).append("linearGradient")
				.attr("id", "gradient")
				.attr("x1", "0%")
				.attr("y1", "0%")
				.attr("x2", "100%")
				.attr("y2", "0%")
				.attr("spreadMethod", "pad")

		gradient.selectAll("stop").data(this.default_colors).enter().append("stop")
			.attr("offset", function(d, i) { return (50 / size) + (100 * i) / size +"%"; })
			.attr("stop-color", function(d) { return d; })
			.attr("stop-opacity", 1)

		this.svg.append("rect")
			.attr("cy", 0)
			.attr("width", this.width)
			.attr("height", this.height)
			.style("fill", "url(#gradient)")

		this.svg.append("circle")
			.attr("cx", this.cursorPos)
			.attr("cy", this.height / 2)
			.attr("stroke", "black")
			.attr("fill", "none")
			.attr("r", this.indexWidth / 2 - 2);

		this.updateRanges(this.selectedIndices[0]);
		this.setColor(this.assignedColors[0], 0);
	},

	hexToRgb: function(hex) {
	    // Expand shorthand form (e.g. "03F") to full form (e.g. "0033FF")
	    var shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
	    hex = hex.replace(shorthandRegex, function(m, r, g, b) {
	        return r + r + g + g + b + b;
	    });

	    var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
	    return result ? {
	        r: parseInt(result[1], 16),
	        g: parseInt(result[2], 16),
	        b: parseInt(result[3], 16)
	    } : null;
	},

	rgbToHex: function(r, g, b) {
    	return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
	},

	getCursorIndex: function(x){
		var index = Math.round(x / this.indexWidth - 0.5);
		if (index > this.size - 1){
			index = this.size - 1;
		}
		return index;
	},


	setUpListeners: function(){
		var boundHandler = (function(e) { this.handleClick(e)}).bind(this);
		this.svg.on('mousedown', boundHandler);
		this.svg.on('touchstart', boundHandler);

		boundHandler = (function(e) { this.handleDragStart(e)}).bind(this);
		this.svg.on('mousedown', boundHandler);
		this.svg.on('touchstart', boundHandler);

		boundHandler = (function(e) { this.handleDragStop(e)}).bind(this);
		this.svg.on('mouseup', boundHandler);
		this.svg.on('touchend', boundHandler);

		boundHandler = (function(e) { this.handleDrag(e)}).bind(this);
		this.svg.on('mousemove', boundHandler);
		this.svg.on('touchmove', boundHandler);

		boundHandler = (function(e) { this.selectIndicator(e)}).bind(this); 
		$("svg + svg").on('click', boundHandler);


		boundHandler = (function(e) { this.rangeColors()}).bind(this);
		$("#colorrange input").on('input', boundHandler);
	},

	rangeColors: function(){
		var r = parseInt($("#red").val());
		var g = parseInt($("#green").val());
		var b = parseInt($("#blue").val());

		var hex = this.rgbToHex(r, g, b);
		$("#hexinput").val(hex);
		this.setColorRange(hex);
	},

	updateRanges: function(index){
		var hex = this.indicators.selectAll("rect")[0][index].getAttribute("fill");
		$("#hexinput").val(hex);
		var rgb = this.hexToRgb(hex);
		$("#red").val(rgb["r"]);
		$("#green").val(rgb["g"]);
		$("#blue").val(rgb["b"]);
	},

	selectIndicator: function(e){
		var x = this.relativeCoords(e, $("svg + svg").offset())["x"];
		var i = Math.round(x / this.indexWidth - 0.25);

		this.selectedIndices = [i];
		this.drawSelection();
	},

	relativeCoords: function(e, offset){
		if (e.type == "touchstart" | e.type == "touchmove"){
			var relX = e.originalEvent.changedTouches[0].clientX - offset["left"];
		}
		else{
			var relX = e.clientX - offset["left"];
		}
		return {"x": relX};
	},

	handleClick: function(e){
		var pos = this.relativeCoords(e, this.jsvg.offset());
		var index = this.getCursorIndex(pos["x"]);

		this.cursorIndex = index;
		this.cursorPos = this.cursorIndex * this.indexWidth + this.indexWidth / 2;

		this.svg.select("circle")
			.attr("cx", this.cursorPos);

		if (!this.mouseHeld){
			if (e.ctrlKey){
				this.selectedIndices.push(this.cursorIndex);
			}else if (e.shiftKey){
				var start = this.selectedIndices[0];
				this.selectedIndices = [];
				console.log(start, this.cursorIndex, Math.min(start, this.cursorIndex), Math.max(this.cursorIndex + 1, start + 1))
				for (var i = Math.min(start, this.cursorIndex); i < Math.max(this.cursorIndex + 1, start + 1); ++i){
					this.selectedIndices.push(i);
				}
			}else{
				this.selectedIndices = [this.cursorIndex];
			}

			this.drawSelection();
		}
	},

	handleDrag: function(e){
		if (this.mouseHeld){
			this.handleClick(e);
			this.endIndex = this.cursorIndex;
			if (this.endIndex < this.startIndex){
				var start = this.endIndex;
				var end = this.startIndex;
			}else{
				var start = this.startIndex;
				var end = this.endIndex;
			}

			var selected = [];
			for (var i = start; i < end + 1; ++i){
				selected.push(i);
			}

			if (e.ctrlKey){
				for (var i = 0; i < selected.length; ++i){
					if (this.selectedIndices.indexOf(selected[i]) === -1){
						this.selectedIndices.push(selected[i]);
					}
				}
			}else{
				this.selectedIndices = selected;
			}

			this.drawSelection();
		}
	},

	handleDragStart: function(e){
		this.startIndex = this.cursorIndex;
		this.mouseHeld = true;
	},

	handleDragStop: function(e){
		this.mouseHeld = false;
	},

	updateColors: function(data){
		var iWidth = this.indexWidth;

		this.svg.selectAll("stop").data(data)
			.attr("stop-color", function(d) { return d; })

		this.indicators.selectAll("rect").data(this.assignedColors)
			.attr("fill", function(d, i) { 
				if (d != "none"){
					return d;
				}else{
					return data[i];
				}
			})
			.attr("stroke", function(d){
				if (d != "none"){
					return "none";
				}else{
					return "#000";
				}
			})
			.attr("stroke-width", 3)
			.attr("width", this.indexWidth / 2)
			.attr("x", function(d, i) { return i * iWidth + iWidth / 4; })
			.attr("height", this.height / 2);
	},

	getColors: function(){
		var cols = [];
		var stops = this.svg.selectAll("stop");
		for (var i = 0; i < this.size; ++i){
			cols[i] = stops[0][i].getAttribute("stop-color");
		}
		return cols;
	},

	setColor: function(color, index){
		cols = [];
		this.assignedColors[index] = color;
		var lastNotNone = 0;
		for (var i = 0; i < this.size; ++i){
			if (this.assignedColors[i] == "none"){
				var nextNotNone = 0;
				for (var j = i; j < this.size; ++j){
					if (this.assignedColors[j] != "none"){
						nextNotNone = j;
						break;
					}
				}
				range = d3.scale.linear().domain([lastNotNone, nextNotNone]).range([this.assignedColors[lastNotNone], this.assignedColors[nextNotNone]]);
				cols[i] = range(i);
			}else{
				lastNotNone = i;
				cols[i] = this.assignedColors[i];
			}
		}
		this.updateColors(cols);
	},

	setColorRange: function(color){
		for (var i = 0; i < this.selectedIndices.length; ++i){
			this.setColor(color, this.selectedIndices[i]);
		}
	},

	setColorToDefault: function(){
		for (var i = 0; i < this.size; ++i){
			this.setColor(this.default_colors[i], i);
		}
	},

	drawSelection: function(){
		this.updateRanges(this.selectedIndices[0]);
		var width = this.indexWidth;
		var select = this.svg.selectAll("circle").data(this.selectedIndices)
			.attr("cx", function(d, i) { return d * width + width / 2; });

		select.enter().append("circle")
			.attr("cx", function(d, i) { return d * width + width / 2; })
			.attr("cy", this.height / 2)
			.attr("stroke", "black")
			.attr("fill", "none")
			.attr("r", this.indexWidth / 2 - 2);

		select.exit().remove();
	}
}