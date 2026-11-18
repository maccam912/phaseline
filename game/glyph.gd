extends RefCounted

# All glyphs use a common 24-unit grid.
static func draw(canvas: CanvasItem, name: String, at: Vector2, extent: float, color: Color) -> void:
	var factor := extent / 24.0
	var paths := []
	match name:
		"brand":
			paths = [[Vector2(0,13),Vector2(5,13),Vector2(10,4),Vector2(9,19),Vector2(15,5),Vector2(14,20),Vector2(19,12),Vector2(24,12)]]
		"disc":
			canvas.draw_arc(at+Vector2(12,12)*factor, 8.6*factor,0,TAU,42,color,1.55*factor,true)
			canvas.draw_arc(at+Vector2(12,12)*factor, 2.7*factor,0,TAU,24,color,1.55*factor,true)
			canvas.draw_arc(at+Vector2(12,12)*factor, 6.1*factor,PI,PI*1.45,18,color,1.4*factor,true)
		"gear":
			var ring := PackedVector2Array()
			for i in 48:
				var angle := i * TAU / 48.0
				var radius := 9.2 if (i % 6) in [0,1,2] else 7.1
				ring.append(at + (Vector2(12,12)+Vector2.from_angle(angle)*radius)*factor)
			ring.append(ring[0])
			canvas.draw_polyline(ring,color,1.45*factor,true)
			canvas.draw_arc(at+Vector2(12,12)*factor,3*factor,0,TAU,24,color,1.5*factor,true)
		"help":
			paths = [[Vector2(3,5),Vector2(8,5),Vector2(12,7),Vector2(16,5),Vector2(21,5),Vector2(21,18),Vector2(16,18),Vector2(12,20),Vector2(8,18),Vector2(3,18),Vector2(3,5)], [Vector2(12,7),Vector2(12,20)]]
		"exit":
			paths = [[Vector2(11,4),Vector2(4,4),Vector2(4,20),Vector2(11,20)],[Vector2(9,12),Vector2(21,12),Vector2(16,7)],[Vector2(21,12),Vector2(16,17)]]
		"music":
			paths = [[Vector2(8,15),Vector2(8,6),Vector2(19,4),Vector2(19,13)],[Vector2(8,9),Vector2(19,7)]]
			for p in [Vector2(5.8,16),Vector2(16.8,14)]:
				canvas.draw_circle(at+p*factor,2.9*factor,color,true,-1,true)
		"clock":
			canvas.draw_arc(at+Vector2(12,12)*factor,8.5*factor,0,TAU,32,color,1.7*factor,true)
			paths = [[Vector2(12,6),Vector2(12,12),Vector2(16,14)]]
		"bpm":
			paths = [[Vector2(2,13),Vector2(7,13),Vector2(10,5),Vector2(14,19),Vector2(17,11),Vector2(22,11)]]
		"best":
			paths = [[Vector2(6,4),Vector2(18,4),Vector2(17,12),Vector2(12,15),Vector2(7,12),Vector2(6,4)], [Vector2(12,15),Vector2(12,20)],[Vector2(8,20),Vector2(16,20)], [Vector2(6,6),Vector2(2,6),Vector2(3,10),Vector2(7,11)],[Vector2(18,6),Vector2(22,6),Vector2(21,10),Vector2(17,11)]]
		"sliders":
			for i in 3:
				var x := 5.0 + i*7
				var y := [10,15,8][i] as float
				paths.append([Vector2(x,3),Vector2(x,y-2)])
				paths.append([Vector2(x,y+2),Vector2(x,21)])
				canvas.draw_rect(Rect2(at+Vector2(x-2,y-2)*factor,Vector2(4,4)*factor),color,true)
		"stack":
			paths = [[Vector2(3,6),Vector2(21,6)],[Vector2(3,12),Vector2(18,12)],[Vector2(3,18),Vector2(15,18)]]
		"headphones":
			canvas.draw_arc(at+Vector2(12,12)*factor,8*factor,PI,TAU,28,color,1.6*factor,true)
			paths = [[Vector2(4,12),Vector2(7,12),Vector2(7,19),Vector2(4,18),Vector2(4,12)],[Vector2(20,12),Vector2(17,12),Vector2(17,19),Vector2(20,18),Vector2(20,12)]]
		"play":
			canvas.draw_colored_polygon(PackedVector2Array([at+Vector2(7,4)*factor,at+Vector2(20,12)*factor,at+Vector2(7,20)*factor]),color)
		"pause":
			for x in [6,14]:
				canvas.draw_rect(Rect2(at+Vector2(x,4)*factor,Vector2(4,16)*factor),color)
		"chevron":
			paths = [[Vector2(9,5),Vector2(16,12),Vector2(9,19)]]
	for path in paths:
		var points := PackedVector2Array()
		for point in path:
			points.append(at+point*factor)
		canvas.draw_polyline(points,color,2.2*factor if name == "brand" else 1.65*factor,true)
