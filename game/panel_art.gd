extends Control

const Glyph := preload("res://game/glyph.gd")
const LIME := Color("#c3fa68")
const LILAC := Color("#c8b3ed")
const PAPER := Color("#f2f3e9")
const GRID := Color("#343b36")
const Lanes := preload("res://game/lanes.gd")

var mode := "guide"
var keys: Array = []
var grade := ""
var offsets: Array = []
var display_font: Font
var mono_font: Font

func _draw() -> void:
	match mode:
		"brand":
			Glyph.draw(self, "brand", Vector2(0, (size.y - 45) * 0.5), 45, LIME)
		"grade":
			_draw_grade()
		"offset":
			_draw_offsets()
		_:
			_draw_lanes()

func _draw_offsets() -> void:
	var from := 7.0
	var to := size.x - from
	var middle := (from + to) * 0.5
	draw_line(Vector2(from, 46), Vector2(to, 46), GRID, 1.5)
	for i in range(13):
		var x := lerpf(from, to, i / 12.0)
		var half_height := 25.0 if i == 6 else (7.0 if i % 3 == 0 else 3.0)
		draw_line(Vector2(x, 46 - half_height), Vector2(x, 46 + half_height), LIME if i == 6 else GRID, 1)
	if mono_font:
		draw_string(mono_font, Vector2(from, 14), "EARLY", HORIZONTAL_ALIGNMENT_LEFT, -1, 11, LILAC)
		draw_string(mono_font, Vector2(middle - 52, 14), "ON BEAT", HORIZONTAL_ALIGNMENT_CENTER, 104, 11, LIME)
		draw_string(mono_font, Vector2(to - 70, 14), "LATE", HORIZONTAL_ALIGNMENT_RIGHT, 70, 11, LILAC)
	for i in range(offsets.size()):
		var x := lerpf(from, to, clampf((float(offsets[i]) + 300) / 600.0, 0, 1))
		var active := i + 1 == offsets.size()
		draw_circle(Vector2(x, 34 + (i % 4) * 8), 5 if active else 3.5, PAPER if active else LILAC, true, -1, true)

func _draw_grade() -> void:
	var center := size * Vector2(0.5, 0.50)
	var radius := minf(size.x * 0.39, size.y * 0.42)
	for index in range(4):
		draw_arc(center, radius * (0.64 + index * 0.12), 0, TAU, 96, GRID, 1, true)
	for index in range(60):
		var direction := Vector2.from_angle(TAU * index / 60.0)
		var tick_length := 5.0 if index % 5 == 0 else 2.0
		draw_line(center + direction * (radius + 4), center + direction * (radius + 4 + tick_length), LILAC if index % 5 == 0 else GRID, 1, true)
	draw_arc(center, radius, -1.48, 0.1, 36, LIME, 2.3, true)
	draw_arc(center, radius, 1.65, 3.25, 36, LIME, 2.3, true)
	if display_font:
		_center_text(grade, center, display_font, int(radius * 1.17), PAPER)

func _track_position(lane: float, progress: float) -> Vector2:
	var near_width := size.x * 0.96
	var far_width := size.x * 0.46
	var width := lerpf(far_width, near_width, progress)
	return Vector2(size.x * 0.5 + (lane / Lanes.KEYS.size() - 0.5) * width, lerpf(11.0, size.y - 45.0, progress))

func _draw_lanes() -> void:
	var count := Lanes.KEYS.size()
	for lane in range(count):
		var points := PackedVector2Array([_track_position(lane, 0.0), _track_position(lane + 1, 0.0), _track_position(lane + 1, 1.0), _track_position(lane, 1.0)])
		draw_colored_polygon(points, Color("#1e2421") if lane % 2 == 0 else Color("#181d1a"))
	for lane in range(count + 1):
		var center_divider := lane == Lanes.HAND_SPLIT
		draw_line(_track_position(lane, 0.0), _track_position(lane, 1.0), Color("#65716b") if center_divider else GRID, 2.5 if center_divider else 1.2, true)
	for row in [0.06, 0.18, 0.34, 0.55, 0.81]:
		draw_line(_track_position(0, row), _track_position(count, row), GRID, 1, true)
	var tail := PackedVector2Array([_track_position(6.30, 0.27), _track_position(6.7, 0.27), _track_position(6.76, 0.72), _track_position(6.24, 0.72)])
	draw_colored_polygon(tail, Lanes.COLORS[6].darkened(0.51))
	draw_line(_track_position(6.5, 0.28), _track_position(6.5, 0.71), Lanes.COLORS[6], 1.3, true)
	_draw_note(3, 0.94)
	_draw_note(6, 0.72)
	_draw_note(8, 0.47)
	_draw_note(1, 0.15)
	draw_line(_track_position(0, 0.97), _track_position(count, 0.97), PAPER, 2, true)
	var key_y := size.y - 21.0
	var key_width := minf(37.0, size.x * 0.082)
	for lane in range(count):
		var x := _track_position(lane + 0.5, 1.0).x
		var cap := Rect2(x - key_width * 0.5, key_y - 13, key_width, 26)
		draw_rect(cap, Color("#272d29"))
		if lane in [3, 6]:
			draw_line(Vector2(x - 4, key_y + 9), Vector2(x + 4, key_y + 9), Lanes.COLORS[lane], 1.5, true)
		if mono_font and lane < keys.size():
			_center_text(keys[lane], Vector2(x, key_y), mono_font, 14, Lanes.COLORS[lane])

func _draw_note(lane: int, progress: float) -> void:
	var points := PackedVector2Array([_track_position(lane + 0.11, progress - 0.02), _track_position(lane + 0.89, progress - 0.02), _track_position(lane + 0.91, progress + 0.013), _track_position(lane + 0.09, progress + 0.013)])
	draw_colored_polygon(points, Lanes.COLORS[lane])

func _center_text(content: String, center: Vector2, font: Font, font_size: int, color: Color) -> void:
	var baseline := center.y + (font.get_ascent(font_size) - font.get_descent(font_size)) * 0.5
	var width := size.x if mode == "grade" else 48.0
	draw_string(font, Vector2(center.x - width * 0.5, baseline), content, HORIZONTAL_ALIGNMENT_CENTER, width, font_size, color)
