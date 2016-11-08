var AuxierreFramework = {
	init: function(params){
		this.visualisations = params["visualisations"];
		this.wavesurfer = params["wavesurfer"];
		this.colorpicker = params["colorpicker"];
		this.timerContainer = params["timerContainer"] || "";
		this.fullscreenSurface = params["fullscreen"] || "";

		this.active;
		this.updateInterval;
		this.songLoaded = false;
		this.playOnLoad = false;

		this.transformData = [];
		this.timePerSegment;
		this.lastIndex = 0;
		this.totalLength;
		this.sim;
		this.simkeys;
		this.lastJump = 0;
		this.lastCheck = 0;
		this.endless = false;
		this.fullscreen = false;

		$("body").prepend("<div id='fullscreen'>\
				<div class='btn-group' role='group' id='media'>\
					<button class='btn btn-default play'><span class='glyphicon glyphicon-play audiocontrol'></span></button>\
					<button class='btn btn-default pause'><span class='glyphicon glyphicon-pause audiocontrol'></button>\
					<button class='btn btn-default stop'><span class='glyphicon glyphicon-stop audiocontrol'></button>\
					<button class='btn btn-default fullscreenButton'><span class='glyphicon glyphicon-fullscreen'></span></button>\
				</div>\
			</div>");
		var width = $('body').innerWidth();
		var height = $('body').innerHeight();
		var container = d3.select("#fullscreen").append("svg").attr("width", width).attr("height", height);
		container.append("rect").attr("x", 0).attr("y", 0).attr("width", width).attr("height", height).attr("fill", "white");
	},

	getData: function(){
		// Gets transformation data asynchronously from the webserver
		$.ajax({
			context: this,
			url: '/songinfo/' + this.songId,
			type: "GET",
			data: {"lastIndex": this.lastIndex},
			success: function(data){
				this.transformData = this.transformData.concat(data["transformData"]);
				this.lastIndex = data["lastIndex"];
				this.totalLength = data["length"];
				this.timePerSegment = data["timePerSegment"];
				for (var i = 0; i < Object.keys(this.visualisations).length; ++i){
					$(this.visualisations[Object.keys(this.visualisations)[i]]).trigger("newData");
				}
				if (!data["finished"]){
					window.setTimeout(this.getData, 5000);
				}else{
					this.similarity();
					for (var i = 0; i < Object.keys(this.visualisations).length; ++i){
						$(this.visualisations[Object.keys(this.visualisations)[i]]).trigger("dataLoaded");
					}
				}
			}
		})
	},

	changeActive: function(newActive){
		if (Object.keys(this.visualisations).indexOf(newActive) != -1){
			this.active = newActive;
			$(this.visualisations[newActive]).trigger("activated");		
		}
	},

	update: function(){
		if (this.visualisations[this.active] !== undefined){
			if (this.fullscreen){
				this.visualisations[this.active].draw(this.getTimeIndex(), this.fullscreenSurface);
			}else{
				this.visualisations[this.active].draw(this.getTimeIndex());
			}
		}
		this.updateDuration();		

		if (this.endless){
			var t = this.getTimeIndex() / 20;
			var kIndex = this.simkeys.indexOf(t+"");
			if (this.lastCheck != t){
				this.lastCheck = t;
				if (kIndex > -1){
					this.lastCheck = t;
					var q = Math.floor(Math.random() * (this.sim[t].length * (1 - kIndex / (this.simkeys.length - 2))));
					var c = this.sim[t][q];
					var time_index = Math.floor(c * this.timePerSegment);
					var prob = d3.scale.linear().domain([this.lastJump, this.simkeys[this.simkeys.length - 2] - 1]).range([0, 1]);

					var likely = prob(t);
					if (t > c){
						likely *= 1.5;
					}
					if (Math.random() > 1 - likely &&this.simkeys.indexOf(c+"") < this.simkeys.length - 2 && (c - t < this.transformData.length / 40 && c > t || c < 0.75 * this.transformData.length / 20 || t > c)){
						this.lastCheck = c;
						this.lastJump = c;
						console.log("Jumped from", t, "to", c, "with a likelihood of", likely, "and a lastJump of", this.lastJump);
						this.wavesurfer.play(time_index / 1000);
					}else{
						console.log("Skipped jump from", t, "to", c, "with a likelihood of", likely, "and a lastJump of", this.lastJump);

					}
				}
			}
		}
		this.updateInterval = window.setTimeout(this.update.bind(this), this.timePerSegment - 10);
	},

	fullscreenToggle: function(){
		if (!this.fullscreen){
			this.fullscreen = true;
			$("#fullscreen").css("display", "block");
			$("#wrap").css("display", "none");
			$("#footer").css("display", "none");
			for (var i = 0; i < Object.keys(this.visualisations).length; ++i){
				$(this.visualisations[Object.keys(this.visualisations)[i]]).trigger("fullscreenOn", ["#fullscreen svg"]);
			}
		}else{
			this.fullscreen = false;
			$("#fullscreen").css("display", "none");
			$("#wrap").css("display", "block");
			$("#footer").css("display", "block");
			for (var i = 0; i < Object.keys(this.visualisations).length; ++i){
				$(this.visualisations[Object.keys(this.visualisations)[i]]).trigger("fullscreenOff");
			}
		}
	},

	getTimeIndex: function(){
		// Gets the index of the data corresponding to the current time of the music player
		var currTime = this.wavesurfer.getCurrentTime();
		return 20 * Math.round(1000 * currTime / this.timePerSegment);
	},

	getDataRange: function(offset){
		// Gets the slice of 11 values corresponding to the current time of the music player
		offset = typeof offset !== 'undefined' ? offset: 0;
		var time = this.getTimeIndex();
		return this.transformData.slice(time + offset * 20, time + 20 + offset * 20);
	},

	updateDuration: function(){
		var time = this.wavesurfer.getCurrentTime();
		var minutes = this.pad(Math.floor(time / 60), 2);
		var second = this.pad(Math.floor(time % 60), 2);
		$(this.timerContainer).text(minutes+":"+second);
	},

	pad: function(num, size){
		var s = num+"";
		while (s.length < size){
			s = "0" + s;
		}
		return s;
	},

	calcSflux: function(abs){
		var fluxes = [];
		for (var i = 0; i < this.lastIndex / 20; ++i){
			var thisSeg = d3.sum(this.transformData.slice(i * 20, i * 20 +20));
			var lastSeg = d3.sum(this.transformData.slice((i - 1) * 20, i * 20));
			if (abs){
				fluxes.push(Math.max(0, thisSeg - lastSeg));
			}else{
				fluxes.push(thisSeg - lastSeg);
			}
		}
		return fluxes;
	},

	calcSfluxThreshold: function(threshold, length, abs){
		length = typeof length !== 'undefined' ? length: 11;
		abs = typeof abs !== 'undefined' ? abs: true;

		var fluxThreshold = [];
		var fluxes = this.calcSflux(abs);
		for (var i = 0; i < fluxes.length; ++i){
			fluxThreshold.push(Math.max(0, d3.mean(fluxes.slice(Math.max(0, i - (length - 1) / 2), i + (length - 1) / 2))) * threshold);
		}
		return [fluxes, fluxThreshold];
	},

	similarity: function(threshold, length, ratioThreshold){
		threshold = typeof threshold !== 'undefined' ? threshold: 2;
		length = typeof length !== 'undefined' ? length: 11;
		ratioThreshold = typeof ratioThreshold !== 'undefined' ? ratioThreshold: 0.925;

		var result = this.calcSfluxThreshold(threshold, length, true);
		var fluxes = result[0];
		var beatThreshold = result[1];

		var interesting = [];
		for (var i = 0; i < fluxes.length; ++i){
			if (fluxes[i] > beatThreshold[i] && fluxes[i] > 0){
				interesting.push(i);
			}
		}
		var interestingData = [];
		for (var i = 0; i < interesting.length; ++i){
			interestingData[i] = this.transformData.slice(interesting[i] * 20, Math.min(interesting[i] * 20 + 80, interesting[i + 1] * 20));
		}
		var total = 0; 
		var similar = 0;
		var simIndex = {};
		for (var i = 0; i < interestingData.length; ++i){
			for (var j = i + 1; j < interestingData.length; ++j){
				var sim = 0;
				var tot = 0;
				for (var x = 0; x < Math.min(interestingData[i].length, interestingData[j].length); ++x){
					if (interestingData[i][x] != 0 || interestingData[j][x] != 0){
						sim += (interestingData[i][x] + interestingData[j][x]) * (Math.min(interestingData[i][x], interestingData[j][x]) / Math.max(interestingData[i][x], interestingData[j][x]));
						tot += interestingData[i][x] + interestingData[j][x];
					}
				}
				if (sim / tot > ratioThreshold){
					total++;
					similar++;
					if (Object.keys(simIndex).indexOf(interesting[i] +"") == -1){
						simIndex[interesting[i]] = [];
					}
					simIndex[interesting[j]] = [interesting[i]];
					simIndex[interesting[i]].push(interesting[j]);
				}else{
					total++;
				}
			}
		}
		simIndex["ratio"] = similar / total;
		this.simkeys = Object.keys(simIndex);
		this.sim = simIndex; 
	}
}

var SpectrumVisualisation = {
	init: function(params){
		this.chart = params["container"];
		this.surface = params["container"];
		this.framework = params["framework"];

		this.y = d3.scale.linear();
		this.colorSize = d3.scale.linear();

		$(this).on('newData', function(){
			this.y.domain([0, d3.max(this.framework.transformData)]);
			this.colorSize.domain([0, d3.max(this.framework.transformData)]);
		}.bind(this));

		$(this).on('activated', function(){
			this.calcDimensions();
		}).bind(this);

		$(this).on('fullscreenOn', function(e, fullChart){
			d3.select("#fullscreen svg").selectAll("g").select("rect").attr("height", 0);
			this.oldChart = this.chart;
			this.chart = fullChart;
			this.calcDimensions(true);
		}.bind(this));

		$(this).on('fullscreenOff', function(){
			this.chart = this.oldChart;
			this.calcDimensions(false);
		}.bind(this));
	},

	calcDimensions: function(fullscreen){
		fullscreen = typeof fullscreen !== 'undefined' ? fullscreen: false;

		if (!fullscreen){
			if ($(window).height() > 768){
				$(this.chart).height($(window).height() - $("hr").offset()["top"] - 30 - 60);
			}else{
				$(this.chart).height($(window).height() / 2);
			}
		}else{
			$(this.chart).height($('body').innerHeight());
			$(this.chart).width($('body').innerWidth());
		}
		this.width = $(this.chart).width();
		this.height = $(this.chart).height();
	},

	draw: function(timeIndex){

		this.y.range([this.height, 0]);
		var y = this.y
		var height = this.height;
		var data = this.framework.getDataRange();
		var colorpicker = this.framework.colorpicker;
		var surface = d3.select(this.chart);

		var barWidth = this.width / data.length;

		var color = colorpicker.getColors();
		var colorSize = this.colorSize;

		var bar = surface.selectAll("g")
			.data(data)
			.attr("transform", function(d, i) { return "translate(" + i * barWidth + ",0)"; })
		.enter().append("g")
			.attr("transform", function(d, i) { return "translate(" + i * barWidth + ",0)"; });

		bar.append("rect")
	      .attr("y", function(d) { return y(d); })
	      .attr("height", function(d) { return height - y(d); })
	      .attr("width", barWidth - 1)
	      .attr("fill", function(d, i){
	      	var rgb = colorpicker.hexToRgb(color[i]);
	      	return "rgb("+rgb["r"] * colorSize(d)+","+rgb["g"]*colorSize(d)+","+rgb["b"]*colorSize(d)+")";});

	    surface.selectAll("g").data(data).select("rect")
	      .transition()
	      .attr("y", function(d) { return y(d); })
	      .attr("height", function(d) { return height - y(d); })
	      .attr("fill", function(d, i){ 
	      	var rgb = colorpicker.hexToRgb(color[i]);
	      	d = Math.pow(1.6, d);
	      	return "rgb("+rgb["r"] * colorSize(d)+","+rgb["g"]*colorSize(d)+","+rgb["b"]*colorSize(d)+")";})
	      .duration(100)
	      .ease("linear");
	}
}

var BeatPulseVisualisation = {
	init: function(params){
		this.chart = params["container"];
		this.framework = params["framework"];
		this.drawDelay = params["drawDelay"] || 700;
		this.x = d3.scale.linear();
		this.circleCounter = 0;
		this.circleAmount = 20;

		$(this).on('newData', function(){
			this.calcFlux(1.5, 11);
		}.bind(this));

		$(this).on('activated', function(){
			this.calcDimensions();
		}).bind(this);

		$(this).on('fullscreenOn', function(e, fullChart){
			this.oldChart = this.chart;
			this.chart = fullChart;
			this.drawCircles();
			this.calcDimensions(true);
		}.bind(this));

		$(this).on('fullscreenOff', function(){
			this.chart = this.oldChart;
			this.calcDimensions(false);
		}.bind(this));
	},

	calcDimensions: function(fullscreen){
		fullscreen = typeof fullscreen !== 'undefined' ? fullscreen: false;

		if (!fullscreen){
			if ($(window).height() > 768){
				$(this.chart).height($(window).height() - $("hr").offset()["top"] - 30 - 60);
			}else{
				$(this.chart).height($(window).height() / 2);
			}
		}
		this.width = $(this.chart).width();
		this.height = $(this.chart).height(); 
	},

	draw: function(timeIndex){

		timeIndex /= 20;
		if (this.width > 768){
			this.x.range([0, this.width / 2]);
		}else{
			this.x.range([0, this.width]);
		}
		var surface = d3.select(this.chart);
		var flux = this.fluxes[timeIndex];
		var threshold = this.fluxThreshold[timeIndex];
		if (flux > threshold && flux > 0){
			var colors = this.framework.colorpicker.getColors();
			var current = this.framework.getDataRange();
			var last = this.framework.getDataRange(-1);
			var max = 0;
			var max_i = 0;
			for (var i = 0; i < current.length; ++i){
				if (current[i] - last[i] > max){
					max = current[i] - last[i];
					max_i = i;
				}
			}
			var x = this.x
			var drawDelay = this.drawDelay;
			var diff = [flux];
			var width = this.width;
			var height = this.height;
			surface.selectAll("circle.c"+this.circleCounter).data(diff)
				.attr("cx", width / 2)
				.attr("cy", height / 2)
				.attr("r", 0)
				.attr("opacity", 1)
				.attr("stroke", colors[max_i])
				.attr("stroke-width", 1)
				//.attr("cx", (max_i + 1) * width / circleAmount)
				.transition()
				.attr("r", function(d) { return x(d); })
				.attr("stroke-width", function(d) { return x(d) / 45 * 2 * (2.9 - max_i / 10); })
				.attr("opacity", 0)
				.duration(function(d, i) { return drawDelay - max_i * 10;})
				.delay(0)
				.ease("linear")
			this.circleCounter = (this.circleCounter + 1) % this.circleAmount;
		}
	},

	drawCircles: function(){
		var surface = d3.select(this.chart);
		if (surface.selectAll("circle")[0].length === 0){
			this.calcDimensions(true);
			var width = this.width;
			var height = this.height;
			for (var i = 0; i < this.circleAmount; ++i){
				surface.append("circle")
					.attr("class", "c"+i)
					.attr("cx", width / 2)
					.attr("cy", height / 2)
					.attr("fill", "none")
					.attr("stroke-width", "4px");
			}
		}
	},

	calcFlux: function(threshold, length){
		this.drawCircles();

		var result = this.framework.calcSfluxThreshold(threshold, length, false);
		this.fluxes = result[0];
		this.fluxThreshold = result[1];
		this.x.domain([0, d3.max(this.fluxes) - d3.max(this.fluxThreshold)]);
	}
}