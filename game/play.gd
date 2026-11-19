extends Control

signal finished(result: Dictionary)
signal exited

enum Mode { COUNT_IN, PLAYING, PAUSED, COMPLETE, ERROR }
enum NoteState { UPCOMING, SUSTAINING, RESOLVED }

const Glyph = preload("res://game/glyph.gd")
const Lanes = preload("res://game/lanes.gd")
const PERFECT_WINDOW := 0.065
const GOOD_WINDOW := 0.145
const STAGE_SIZE := Vector2(1280, 800)
const HORIZON := 244.0
const TARGET := 630.0
const TOUCH_PAD_HEIGHT := 104.0
# Depth in seconds at constant forward speed. Zero time is the judgment line.
const CAMERA_DISTANCE := 0.84
const FAR_ROAD := 24.0
const HEAD_HALF_DEPTH := 0.008
const CENTER := 640.0
const INK := Color("#101214")
const PAPER := Color("#eff2eb")
const MUTE := Color("#a1a8aa")
const LIME := Color("#d2fb66")
const VIOLET := Color("#ba9afa")
const LINE := Color("#363c3c")
const PAUSE_RECT := Rect2(1088, 26, 148, 42)
const MENU_RECTS := [Rect2(447, 351, 386, 53), Rect2(447, 416, 386, 53), Rect2(447, 481, 386, 53)]

var _touch_layout := OS.has_feature("android")
var _lane_width := 100.0
var _display: Font
var _mono: Font
var _headline: Font
var _cover: Texture2D
var _track: Dictionary
var _difficulty: String
var _keys: Array = Lanes.KEYS
var _key_labels: Array[String] = []
var _notes: Array[Dictionary] = []
var _next_miss := 0
var _active_hold: Array[int] = []
var _sources: Dictionary = {}
var _touch_lane_counts: Array[int] = []
var _lights: Array[float] = []
var _last_strikes: Array[float] = []
var _lane_results: Array[String] = []
var _music: AudioStreamPlayer
var _fx: Array[AudioStreamPlayer] = []
var _click: AudioStreamPlayer
var _mode := Mode.COMPLETE
var _before_pause := Mode.COUNT_IN
var _count := 0.0
var _count_tick := 0
var _returning := false
var _song_time := 0.0
var _duration := 0.0
var _final_chart_time := 0.0
var _audio_done := false
var _tail_tick := 0
var _tail_from := 0.0
var _latency := 0.0
var _offset := 0.0
var _beat := 0.5
var _beat_origin := 0.0
var _beats_per_bar := 4
var _scene_color := VIOLET
var _approach := 3.0
var _reduced := false
var _perfect := 0
var _good := 0
var _miss := 0
var _combo := 0
var _max_combo := 0
var _feedback := ""
var _timing_feedback := ""
var _feedback_time := 0.0
var _streak_time := 0.0
var _streak_count := 0
var _pause_choice := 0
var _mouse_at := Vector2(-1000, -1000)
var _hold_grace_until := -100.0

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	_display = ThemeDB.fallback_font
	_mono = ThemeDB.fallback_font
	if ResourceLoader.exists("res://assets/fonts/display.ttf"):
		_display = load("res://assets/fonts/display.ttf")
	_headline = _display
	if ResourceLoader.exists("res://assets/fonts/headline.ttf"):
		_headline = load("res://assets/fonts/headline.ttf")
	if ResourceLoader.exists("res://assets/fonts/mono.ttf"):
		_mono = load("res://assets/fonts/mono.ttf")
	_music = AudioStreamPlayer.new()
	add_child(_music)
	_music.finished.connect(_audio_finished)
	_active_hold.resize(Lanes.COUNT)
	_active_hold.fill(-1)
	_touch_lane_counts.resize(Lanes.COUNT)
	_lights.resize(Lanes.COUNT)
	_last_strikes.resize(Lanes.COUNT)
	_lane_results.resize(Lanes.COUNT)
	var hit_sound := _make_tick(680.0, 0.028)
	for lane in Lanes.COUNT:
		var player := AudioStreamPlayer.new()
		add_child(player)
		player.stream = hit_sound
		player.pitch_scale = 0.86 + lane * 0.045
		_fx.append(player)
	_click = AudioStreamPlayer.new()
	add_child(_click)
	_click.stream = _make_tick(920.0, 0.049)

func setup(track: Dictionary, difficulty: String, settings: Dictionary) -> void:
	_track = track
	_difficulty = difficulty.to_lower()
	var bindings: Array = settings.get("keys", Lanes.KEYS)
	_keys = bindings if bindings.size() == Lanes.COUNT else Lanes.KEYS
	_key_labels.clear()
	_lane_width = 120.0 if _touch_layout else 100.0
	for lane in Lanes.COUNT:
		_key_labels.append(str(lane + 1) if _touch_layout else Lanes.key_name(int(_keys[lane])))
	_music.volume_db = linear_to_db(clampf(float(settings.get("music_volume", 0.8)), 0.0, 1.0))
	var sfx_db := linear_to_db(clampf(float(settings.get("sfx_volume", 0.55)), 0.0, 1.0))
	for player in _fx:
		player.volume_db = sfx_db - 8.5
	_click.volume_db = sfx_db - 3.5
	_offset = float(settings.get("offset_ms", 0)) / 1000.0
	_reduced = bool(settings.get("reduced_motion", false))
	_beat = 60.0 / maxf(float(track.get("bpm", 120)), 1.0)
	_beat_origin = float(track.get("beat_origin", 0.0))
	_beats_per_bar = maxi(1, int(track.get("beats_per_bar", 4)))
	_scene_color = Color.from_string(str(track.get("color", "")), VIOLET)
	var cover_path := "res://assets/covers/%s.webp" % str(track.get("id", ""))
	if ResourceLoader.exists(cover_path):
		_cover = load(cover_path)
	_approach = clampf(_beat * 6.0, 2.55, 3.6)
	var path := str(track.get("audio", ""))
	if ResourceLoader.exists(path):
		_music.stream = load(path)
	_start()

func _start() -> void:
	if _music.stream == null:
		_mode = Mode.ERROR
		queue_redraw()
		return
	_music.stop()
	_music.stream_paused = false
	_notes.clear()
	_final_chart_time = 0.0
	for data: Dictionary in _track.get("charts", {}).get(_difficulty, []):
		var t := float(data.t)
		var lane := int(data.l)
		var duration := maxf(0.0, float(data.get("d", 0.0)))
		_notes.append({"t": t, "l": lane, "d": duration, "state": NoteState.UPCOMING, "rating": ""})
		_final_chart_time = maxf(_final_chart_time, t + duration)
	_notes.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return float(a.t) < float(b.t))
	_active_hold.fill(-1)
	_touch_lane_counts.fill(0)
	_lights.fill(0.0)
	_last_strikes.fill(0.0)
	_sources.clear()
	_next_miss = 0
	_perfect = 0
	_good = 0
	_miss = 0
	_combo = 0
	_max_combo = 0
	_feedback_time = 0.0
	_streak_time = 0.0
	_streak_count = 0
	_duration = _music.stream.get_length()
	_hold_grace_until = -100.0
	_audio_done = false
	_returning = false
	_latency = maxf(0.0, AudioServer.get_output_latency())
	_count = _beat * 3.0
	_count_tick = 3
	_song_time = -_count
	_mode = Mode.COUNT_IN
	_countdown_click()

func _process(delta: float) -> void:
	if _mode == Mode.COMPLETE or _mode == Mode.ERROR or _mode == Mode.PAUSED:
		return
	_feedback_time = maxf(0.0, _feedback_time - delta)
	_streak_time = maxf(0.0, _streak_time - delta)
	for lane in Lanes.COUNT:
		_lights[lane] = maxf(0.0, _lights[lane] - delta * 4.4)
		_last_strikes[lane] = maxf(0.0, _last_strikes[lane] - delta * 2.7)
	if _mode == Mode.COUNT_IN:
		_count = maxf(0.0, _count - delta)
		if not _returning:
			_song_time = -_count
		var tick := ceili(_count / _beat)
		if tick > 0 and tick != _count_tick:
			_count_tick = tick
			_countdown_click()
		if _count <= 0:
			_mode = Mode.PLAYING
			if _returning:
				_hold_grace_until = _song_time - _offset + 0.20
				if _audio_done:
					_tail_from = _song_time
					_tail_tick = Time.get_ticks_usec()
				else:
					_music.stream_paused = false
			else:
				_song_time = -_latency
				_music.play()
			_returning = false
	if _mode == Mode.PLAYING:
		_sample_clock()
		_advance(_song_time - _offset)
		if _audio_done and _song_time >= maxf(_duration, _final_chart_time + _offset + GOOD_WINDOW):
			_complete()
	queue_redraw()

func _sample_clock() -> void:
	var now: float
	if _audio_done:
		now = _tail_from + float(Time.get_ticks_usec() - _tail_tick) * 0.000001
	else:
		now = _music.get_playback_position() + AudioServer.get_time_since_last_mix() - _latency
	_song_time = maxf(_song_time, now)

func _audio_finished() -> void:
	_audio_done = true
	_tail_tick = Time.get_ticks_usec()
	_tail_from = maxf(_duration - _latency, _song_time)

func _advance(now: float) -> void:
	while _next_miss < _notes.size() and float(_notes[_next_miss].t) < now - GOOD_WINDOW:
		if _notes[_next_miss].state == NoteState.UPCOMING:
			_resolve(_next_miss, "MISS", "LATE")
		_next_miss += 1
	for lane in Lanes.COUNT:
		var index: int = _active_hold[lane]
		if index < 0:
			continue
		var note := _notes[index]
		if _touch_lane_counts[lane] == 0 and now > _hold_grace_until:
			_resolve(index, "MISS", "RELEASED EARLY")
		elif _touch_lane_counts[lane] > 0 and now >= float(note.t) + float(note.d):
			_resolve(index, note.rating, "HOLD COMPLETE")

func _resolve(index: int, rating: String, timing: String) -> void:
	var note := _notes[index]
	if note.state == NoteState.RESOLVED:
		return
	var lane := int(note.l)
	note.state = NoteState.RESOLVED
	if _active_hold[lane] == index:
		_active_hold[lane] = -1
	match rating:
		"PERFECT":
			_perfect += 1
			_combo += 1
		"GOOD":
			_good += 1
			_combo += 1
		_:
			_miss += 1
			_combo = 0
	_max_combo = maxi(_max_combo, _combo)
	if _combo > 0 and _combo % 25 == 0:
		_streak_count = _combo
		_streak_time = 1.7
	elif _combo == 0:
		_streak_time = 0.0
	_show_feedback(lane, rating, timing)

func _show_feedback(lane: int, rating: String, timing: String) -> void:
	_feedback = rating
	_timing_feedback = timing
	_feedback_time = 0.65
	_last_strikes[lane] = 1.0
	_lane_results[lane] = rating

func _press(source: String, lane: int) -> void:
	if _sources.has(source):
		return
	_sources[source] = lane
	_touch_lane_counts[lane] += 1
	_lights[lane] = 1.0
	if _touch_lane_counts[lane] > 1 or _active_hold[lane] >= 0:
		return
	if _mode == Mode.COUNT_IN and (_returning or _count > GOOD_WINDOW + absf(_offset)):
		return
	if _mode == Mode.PLAYING:
		_sample_clock()
	var now := _song_time - _offset
	_advance(now)
	for index in range(_next_miss, _notes.size()):
		var note := _notes[index]
		var time_error := now - float(note.t)
		if time_error < -GOOD_WINDOW:
			break
		if note.state != NoteState.UPCOMING or int(note.l) != lane or absf(time_error) > GOOD_WINDOW:
			continue
		var rating := "PERFECT" if absf(time_error) <= PERFECT_WINDOW else "GOOD"
		var timing := "ON TIME"
		if absf(time_error) >= 0.018:
			timing = "%s %d MS" % ["EARLY" if time_error < 0 else "LATE", roundi(absf(time_error) * 1000.0)]
		_fx[lane].play()
		if float(note.d) > 0.0:
			note.state = NoteState.SUSTAINING
			note.rating = rating
			_active_hold[lane] = index
			_show_feedback(lane, "HOLD", timing)
		else:
			_resolve(index, rating, timing)
		break

func _release(source: String) -> void:
	if not _sources.has(source):
		return
	var lane := int(_sources[source])
	_sources.erase(source)
	_touch_lane_counts[lane] -= 1
	if _touch_lane_counts[lane] > 0 or _active_hold[lane] < 0 or (_mode == Mode.COUNT_IN and _returning):
		return
	if _mode == Mode.PLAYING:
		_sample_clock()
	var index: int = _active_hold[lane]
	var note := _notes[index]
	var tolerance := minf(0.11, float(note.d) * 0.25)
	if _song_time - _offset >= float(note.t) + float(note.d) - tolerance:
		_resolve(index, note.rating, "HOLD COMPLETE")
	else:
		_resolve(index, "MISS", "RELEASED EARLY")

func _complete() -> void:
	_mode = Mode.COMPLETE
	var accuracy := _accuracy()
	var grade := "D"
	if accuracy >= 95.0:
		grade = "S"
	elif accuracy >= 90.0:
		grade = "A"
	elif accuracy >= 80.0:
		grade = "B"
	elif accuracy >= 65.0:
		grade = "C"
	finished.emit({"score": _score(), "accuracy": accuracy, "perfect": _perfect, "good": _good, "miss": _miss, "max_combo": _max_combo, "grade": grade})

func _score() -> int:
	return roundi(1000000.0 * (float(_perfect) + _good * 0.65) / maxi(1, _notes.size()))

func _accuracy() -> float:
	var judged := _perfect + _good + _miss
	return 100.0 * (float(_perfect) + _good * 0.65) / judged if judged > 0 else 0.0

func _pause() -> void:
	if _mode != Mode.COUNT_IN and _mode != Mode.PLAYING:
		return
	_before_pause = _mode
	if _mode == Mode.PLAYING:
		_sample_clock()
		_music.stream_paused = true
	_click.stop()
	for fx in _fx:
		fx.stop()
	_sources.clear()
	_touch_lane_counts.fill(0)
	_mode = Mode.PAUSED
	_pause_choice = 0
	queue_redraw()

func _resume() -> void:
	_mode = Mode.COUNT_IN
	_returning = _before_pause == Mode.PLAYING or _returning
	if _returning:
		_count = _beat * 3.0
	else:
		_count = maxf(_count, _beat)
	_count_tick = ceili(_count / _beat)
	_countdown_click()
	queue_redraw()

func _menu_action(choice: int) -> void:
	if _mode == Mode.ERROR:
		_leave()
		return
	match choice:
		0: _resume()
		1: _start()
		2: _leave()

func _leave() -> void:
	_mode = Mode.COMPLETE
	_music.stop()
	# Main replaces this screen immediately. Consume the event while our viewport is still attached.
	if is_inside_tree():
		get_viewport().set_input_as_handled()
	exited.emit()

func _notification(what: int) -> void:
	if what in [NOTIFICATION_APPLICATION_FOCUS_OUT, NOTIFICATION_APPLICATION_PAUSED]:
		_pause()

func go_back() -> void:
	if _mode == Mode.ERROR:
		_leave()
	elif _mode == Mode.PAUSED:
		_resume()
	else:
		_pause()

func _input(event: InputEvent) -> void:
	if _mode == Mode.COMPLETE or not is_visible_in_tree():
		return
	var handled := false
	if event is InputEventKey and not event.echo:
		var code: int = event.physical_keycode if event.physical_keycode != 0 else event.keycode
		if code == KEY_ESCAPE and event.pressed:
			go_back()
			handled = true
		elif _mode == Mode.PAUSED or _mode == Mode.ERROR:
			if event.pressed:
				if code in [KEY_UP, KEY_DOWN, KEY_TAB]:
					var step := -1 if (code == KEY_UP or (code == KEY_TAB and event.shift_pressed)) else 1
					_pause_choice = posmod(_pause_choice + step, MENU_RECTS.size())
					queue_redraw()
				elif code in [KEY_ENTER, KEY_KP_ENTER, KEY_SPACE]:
					_menu_action(_pause_choice)
			handled = true
		else:
			var lane := _keys.find(code)
			if lane >= 0:
				var source := "key%d" % code
				if event.pressed:
					_press(source, lane)
				else:
					_release(source)
				handled = true
	elif event is InputEventMouse and event.device == InputEvent.DEVICE_ID_EMULATION:
		# Buttons in the library use emulated clicks. The highway consumes the original touches.
		handled = true
	elif event is InputEventMouseMotion:
		_mouse_at = _stage_point(get_local_mouse_position())
		if _mode == Mode.PAUSED:
			for i in MENU_RECTS.size():
				if MENU_RECTS[i].has_point(_mouse_at):
					_pause_choice = i
		queue_redraw()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		handled = _pointer(_stage_point(get_local_mouse_position()), event.pressed, "mouse")
	elif event is InputEventScreenTouch:
		var local_point: Vector2 = get_global_transform_with_canvas().affine_inverse() * event.position
		handled = _pointer(_stage_point(local_point), event.pressed and not event.canceled, "touch%d" % event.index)
	if handled and is_inside_tree():
		get_viewport().set_input_as_handled()

func _pointer(point: Vector2, pressed: bool, source: String) -> bool:
	if not pressed:
		_release(source)
		return true
	if _mode == Mode.ERROR:
		if MENU_RECTS[1].has_point(point):
			_leave()
		return true
	if _mode == Mode.PAUSED:
		for i in MENU_RECTS.size():
			if MENU_RECTS[i].has_point(point):
				_menu_action(i)
				break
		return true
	if _pause_rect().has_point(point):
		_pause()
		return true
	var pad_bottom := TARGET + (4.0 + TOUCH_PAD_HEIGHT if _touch_layout else 65.0)
	if point.y >= _track_point(Lanes.HAND_SPLIT, FAR_ROAD).y and point.y <= pad_bottom:
		var scale_at_y := minf(1.0, (point.y - HORIZON) / (TARGET - HORIZON))
		var half_width := _lane_width * Lanes.HAND_SPLIT * scale_at_y
		var relative := (point.x - CENTER + half_width) / (half_width * 2.0)
		if relative >= 0.0 and relative < 1.0:
			_press(source, floori(relative * Lanes.COUNT))
			return true
	return false

func _stage_scale() -> float:
	return maxf(0.001, minf(size.x / STAGE_SIZE.x, size.y / STAGE_SIZE.y))

func _pause_rect() -> Rect2:
	return PAUSE_RECT.grow_individual(12, 12, 0, 12) if _touch_layout else PAUSE_RECT

func _stage_point(point: Vector2) -> Vector2:
	return (point - (size - STAGE_SIZE * _stage_scale()) * 0.5) / _stage_scale()

func _countdown_click() -> void:
	_click.pitch_scale = 1.3 if _count_tick == 1 else 1.0
	_click.play()

func _make_tick(hz: float, seconds: float) -> AudioStreamWAV:
	const RATE := 22050
	var frames := ceili(seconds * RATE)
	var samples := PackedByteArray()
	samples.resize(frames * 2)
	for i in frames:
		var t := float(i) / RATE
		var envelope := minf(t / 0.0018, 1.0) * pow(1.0 - float(i) / frames, 3.4)
		var s := (sin(TAU * hz * t) + 0.25 * sin(TAU * hz * 2.56 * t)) * 0.27 * envelope
		samples.encode_s16(i * 2, roundi(s * 32767.0))
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = RATE
	stream.data = samples
	return stream

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), INK)
	if _track.is_empty():
		return
	var scale_factor := _stage_scale()
	draw_set_transform((size - STAGE_SIZE * scale_factor) * 0.5, 0.0, Vector2.ONE * scale_factor)
	_draw_landscape()
	_draw_runway()
	_draw_session()
	if _mode == Mode.COUNT_IN:
		_draw_count()
	if _mode == Mode.PAUSED or _mode == Mode.ERROR:
		_draw_menu()

func _projection_scale(seconds_until: float) -> float:
	return CAMERA_DISTANCE / (CAMERA_DISTANCE + seconds_until)

func _track_point(lane: float, seconds_until: float, elevation: float = 0.0) -> Vector2:
	var at_strike := Vector2((lane - Lanes.HAND_SPLIT) * _lane_width, TARGET - HORIZON - elevation)
	return Vector2(CENTER, HORIZON) + at_strike * _projection_scale(seconds_until)

func _time_at_y(y: float) -> float:
	return CAMERA_DISTANCE * ((TARGET - HORIZON) / (y - HORIZON) - 1.0)

func _quad(a: Vector2, b: Vector2, c: Vector2, d: Vector2, color: Color) -> void:
	draw_colored_polygon(PackedVector2Array([a, b, c, d]), color)

func _gradient(a: Vector2, b: Vector2, c: Vector2, d: Vector2, top: Color, bottom: Color) -> void:
	draw_polygon(PackedVector2Array([a, b, c, d]), PackedColorArray([top, top, bottom, bottom]))

func _text(at: Vector2, value: String, font: Font, font_size: int, color: Color, width: float = -1.0, align: HorizontalAlignment = HORIZONTAL_ALIGNMENT_LEFT) -> void:
	draw_string(font, at, value, align, width, font_size, color)

func _draw_landscape() -> void:
	_gradient(Vector2(0, 90), Vector2(1280, 90), Vector2(1280, 287), Vector2(0, 287), INK, Color("#282432"))
	_gradient(Vector2(0, 287), Vector2(1280, 287), Vector2(1280, 700), Vector2(0, 700), Color("#202024"), INK)
	var track_index := str(_track.get("id", "")).hash() % 97
	for i in 62:
		var x: float = fposmod(i * 433.71 + track_index * 27.21, 1256.0) + 12.0
		var y: float = fposmod(i * 73.34 + track_index * 1.13, 146.0) + 95.0
		var opacity := 0.09 + fposmod(i * 0.053, 0.27)
		draw_circle(Vector2(x, y), 0.65 + fposmod(i * 0.51, 0.65), Color(PAPER, opacity), true, -1, true)
	var center := Vector2(640, 244)
	var pulse := 0.0 if _reduced else pow(1.0 - fposmod((_song_time - _beat_origin) / _beat, 1.0), 3.0)
	var glow := VIOLET.lerp(_scene_color, 0.5)
	for haze in range(3, 0, -1):
		draw_circle(center, 69.0 + haze * 9.0 + pulse * 2.0, Color(glow, 0.026 + pulse * 0.012), true, -1, true)
	var top := glow.lightened(0.43)
	var low := glow.darkened(0.28)
	var radius := 68.0
	# Scan lines widen toward the lower rim of the setting sun.
	for line in 37:
		var dy := -radius + line * (2.0 * radius / 36.0)
		var half := sqrt(maxf(0.0, radius * radius - dy * dy))
		var u := float(line) / 36.0
		draw_line(Vector2(center.x - half, center.y + dy), Vector2(center.x + half, center.y + dy), top.lerp(low, u), lerpf(4.1, 1.1, u), true)
	for row in 3:
		var ridge := PackedVector2Array()
		for n in range(-1, 67):
			var x: float = n * 20.0
			var far_factor := minf(1.0, absf(x - CENTER) / 400.0)
			var shape := sin(n * 0.23 + row * 1.13 + track_index * 0.07) * 0.52 + sin(n * 0.71 + row) * 0.21 + cos(n * 1.61 + row * 2.1) * 0.14
			ridge.append(Vector2(x, 250.0 + row * 13.0 - far_factor * (35.0 - row * 4.0) * (shape + 0.52)))
		var poly := ridge.duplicate()
		poly.append(Vector2(1320, 302 + row * 6))
		poly.append(Vector2(-20, 302 + row * 6))
		draw_colored_polygon(poly, [Color("#34303f"), Color("#2c2934"), Color("#23232a")][row])
		draw_polyline(ridge, [Color("#504457"), Color("#4c4054"), Color("#423c48")][row], 1.0, true)
	var floor_color := Color("#29292e")
	var floor_far := _time_at_y(299.0)
	var floor_near := _time_at_y(700.0)
	for i in range(-36, 37):
		var lane := Lanes.HAND_SPLIT + i * 1.35
		draw_line(_track_point(lane, floor_far), _track_point(lane, floor_near), floor_color, 1.0, true)
	# Fixed scenery shares the same vanishing point as the moving road markings.
	for i in range(14):
		var row_time := floor_near + i * 0.32
		if row_time > floor_far:
			break
		var y := _track_point(Lanes.HAND_SPLIT, row_time).y
		draw_line(Vector2(0, y), Vector2(1280, y), Color(floor_color, 0.60), 1.0)
	# Feather the landscape into the readouts, keeping the playfield unobstructed.
	for side in [-1.0, 1.0]:
		var outside: float = 0.0 if side < 0.0 else STAGE_SIZE.x
		var inside: float = outside - side * 285.0
		var points := PackedVector2Array([Vector2(outside, 315), Vector2(inside, 315), Vector2(inside, 702), Vector2(outside, 702)])
		draw_polygon(points, PackedColorArray([Color(INK, 0.90), Color(INK, 0.0), Color(INK, 0.0), Color(INK, 0.94)]))

func _draw_runway() -> void:
	var now := _song_time - _offset
	_quad(_track_point(-0.055, FAR_ROAD), _track_point(Lanes.COUNT + 0.055, FAR_ROAD), _track_point(Lanes.COUNT + 0.055, 0.0, -9.0), _track_point(-0.055, 0.0, -9.0), Color("#101315"))
	for lane in Lanes.COUNT:
		var hand_tint := Color("#182322") if lane < Lanes.HAND_SPLIT else Color("#201d27")
		var base := hand_tint if lane % 2 == 0 else hand_tint.darkened(0.17)
		_gradient(_track_point(lane, FAR_ROAD), _track_point(lane + 1, FAR_ROAD), _track_point(lane + 1, 0.0), _track_point(lane, 0.0), base.lightened(0.035), base)
		var active: bool = _touch_lane_counts[lane] > 0 or _active_hold[lane] >= 0
		var glow: float = maxf(_lights[lane] * 0.22, 0.13 if active else 0.0)
		if glow > 0.002:
			_gradient(_track_point(lane, 0.67), _track_point(lane + 1, 0.67), _track_point(lane + 1, 0.0), _track_point(lane, 0.0), Color(Lanes.COLORS[lane], 0.0), Color(Lanes.COLORS[lane], glow))
	for edge in range(Lanes.COUNT + 1):
		draw_line(_track_point(edge, FAR_ROAD), _track_point(edge, 0.0), Color("#394140"), 1.3, true)
	for edge in [0.0, float(Lanes.COUNT)]:
		draw_line(_track_point(edge, FAR_ROAD), _track_point(edge, 0.0), Color("#77787e"), 1.6, true)
		var outside: float = -0.037 if edge == 0 else Lanes.COUNT + 0.037
		draw_line(_track_point(outside, FAR_ROAD), _track_point(outside, 0.0), Color(VIOLET, 0.57), 1.2, true)
	var grid_distance := _approach + _beat * 6.0
	var first_beat := ceili((now - _beat_origin) / _beat)
	var last_beat := floori((now + grid_distance - _beat_origin) / _beat)
	for i in range(first_beat, last_beat + 1):
		var dt := _beat_origin + i * _beat - now
		var color := Color("#4b5055") if posmod(i, _beats_per_bar) == 0 else Color("#303538")
		color.a = 1.0 - smoothstep(_approach, grid_distance, dt)
		draw_line(_track_point(0, dt), _track_point(Lanes.COUNT, dt), color, 1.0, true)
	# A dark center rail and its two edges separate the five lanes under each hand.
	var split := float(Lanes.HAND_SPLIT)
	_quad(_track_point(split - 0.032, FAR_ROAD), _track_point(split + 0.032, FAR_ROAD),
		_track_point(split + 0.032, 0.0), _track_point(split - 0.032, 0.0), INK)
	for side in [-1.0, 1.0]:
		var edge: float = split + side * 0.032
		draw_line(_track_point(edge, FAR_ROAD), _track_point(edge, 0.0), Color(Color("#a8aeaa"), 0.74), 1.0, true)
	# Draw farther notes first. A sustaining tail remains visible after its head has passed the miss cursor.
	var visible: Array[int] = []
	for lane in Lanes.COUNT:
		if _active_hold[lane] >= 0 and _active_hold[lane] < _next_miss:
			visible.append(_active_hold[lane])
	for i in range(_next_miss, _notes.size()):
		if float(_notes[i].t) > now + _approach:
			break
		if _notes[i].state != NoteState.RESOLVED:
			visible.append(i)
	visible.reverse()
	for i in visible:
		_draw_note(_notes[i], now)
	for lane in Lanes.COUNT:
		_draw_receptor(lane)
	draw_line(_track_point(0, 0.0), _track_point(Lanes.COUNT, 0.0), Color("#e8ece6"), 2.0)

func _draw_note(note: Dictionary, now: float) -> void:
	var lane := int(note.l)
	var seconds_until := float(note.t) - now
	var held: bool = note.state == NoteState.SUSTAINING
	var head_time := maxf(seconds_until, 0.0) if held else seconds_until
	var color: Color = Lanes.COLORS[lane]
	var arrival_alpha := smoothstep(0.0, 0.22, _approach - head_time)
	color.a = arrival_alpha
	if float(note.d) > 0.0:
		var tail_time := minf(_approach, seconds_until + float(note.d))
		# Clip the ribbon where the key panel hides it. The unplayed head keeps moving.
		var near_time := maxf(head_time, _time_at_y(TARGET + 4.0))
		if tail_time > near_time:
			_gradient(_track_point(lane + 0.29, tail_time), _track_point(lane + 0.71, tail_time), _track_point(lane + 0.71, near_time), _track_point(lane + 0.29, near_time), Color(color, 0.26 * arrival_alpha), Color(color, (0.56 if held else 0.38) * arrival_alpha))
			draw_line(_track_point(lane + 0.5, tail_time), _track_point(lane + 0.5, near_time), Color(color, 0.9 * arrival_alpha), 1.2, true)
			draw_line(_track_point(lane + 0.28, tail_time), _track_point(lane + 0.72, tail_time), color, maxf(1.0, 3.4 * _projection_scale(tail_time)), true)

	var back := head_time + HEAD_HALF_DEPTH
	var front := head_time - HEAD_HALF_DEPTH
	if _track_point(lane + 0.5, back, 4.0).y > TARGET + 4.0:
		return
	# A shallow beveled tile has a fixed width, depth and height in world space.
	var cap := PackedVector2Array([
		_track_point(lane + 0.14, back, 4.0), _track_point(lane + 0.86, back, 4.0),
		_track_point(lane + 0.89, head_time, 1.2), _track_point(lane + 0.86, front, -1.0),
		_track_point(lane + 0.14, front, -1.0), _track_point(lane + 0.11, head_time, 1.2)
	])
	if held:
		draw_line(cap[5], cap[2], Color(color, 0.25), 19.0 * _projection_scale(head_time), true)
	draw_colored_polygon(cap, color)
	draw_line(cap[0], cap[1], color.lightened(0.5), maxf(1.0, 2.0 * _projection_scale(head_time)), true)
	draw_line(_track_point(lane + 0.45, head_time, 1.2), _track_point(lane + 0.55, head_time, 1.2), Color(INK, 0.36 * arrival_alpha), maxf(0.8, 1.8 * _projection_scale(head_time)))

	# The first difficulty teaches the ten-key layout directly on approaching notes.
	if _difficulty == "easy" and head_time < 0.95 and not held and _key_labels[lane].length() <= 2:
		var alpha := 1.0 - smoothstep(0.55, 0.95, head_time)
		var baseline := _track_point(lane + 0.5, back, 9.5)
		var label_size := roundi(lerpf(10.0, 16.0, _projection_scale(maxf(head_time, 0.0))))
		var left := baseline - Vector2(24, 0)
		_text(left + Vector2(0, 1), _key_labels[lane], _mono, label_size, Color(INK, alpha), 48, HORIZONTAL_ALIGNMENT_CENTER)
		_text(left, _key_labels[lane], _mono, label_size, Color(color, alpha), 48, HORIZONTAL_ALIGNMENT_CENTER)

func _draw_receptor(lane: int) -> void:
	var left := _track_point(lane, 0.0).x
	var right := _track_point(lane + 1, 0.0).x
	var mid := (left + right) * 0.5
	var color: Color = Lanes.COLORS[lane]
	var down: bool = _touch_lane_counts[lane] > 0
	var underlay := Rect2(left + 1.5, TARGET + 4, right - left - 3, TOUCH_PAD_HEIGHT if _touch_layout else 56.0)
	draw_rect(underlay, Color("#202529").lerp(color, 0.22 if down else 0.025))
	draw_rect(underlay, Color(color, 0.60 if down else 0.24), false, 1.0)
	draw_rect(Rect2(left + 2, TARGET + 4, right - left - 4, 3.7), color)
	var label := _key_labels[lane] if lane < _key_labels.size() else "?"
	var font_size := 31 if _touch_layout else (24 if label.length() <= 2 else 15)
	while font_size > 10 and _mono.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x > right - left - 8.0:
		font_size -= 1
	var baseline := underlay.get_center().y + (_mono.get_ascent(font_size) - _mono.get_descent(font_size)) * 0.5
	_text(Vector2(left, baseline), label, _mono, font_size, color if down else PAPER, right - left, HORIZONTAL_ALIGNMENT_CENTER)
	if not _touch_layout and lane in [3, 6]:
		draw_rect(Rect2(mid - 8, TARGET + 46, 16, 2.5), Color(color, 0.85))
	var burst: float = _last_strikes[lane]
	if burst > 0.0 and not _reduced:
		var hit_color: Color = Color("#ff8d88") if _lane_results[lane] == "MISS" else color
		for j in 5:
			var x := mid + (j - 2) * 18.0
			var spread := (1.0 - burst) * 16.0
			var drift := Vector2((j - 2) * spread * 0.6, -16.0 - (1.0 - burst) * (18.0 + (j % 2) * 19.0))
			var pos := Vector2(x, TARGET) + drift
			draw_line(pos, pos + Vector2((j - 2) * 1.3, -4), Color(hit_color, burst * 0.9), 1.6, true)

func _draw_session() -> void:
	draw_rect(Rect2(0, 0, 1280, 88), INK)
	draw_line(Vector2(44, 87), Vector2(1236, 87), LINE, 1.0)
	Glyph.draw(self, "brand", Vector2(45, 28), 33, LIME)
	_text(Vector2(88, 56), "PHASELINE", _headline, 32, PAPER)
	draw_circle(Vector2(284, 45), 3.6, LIME, true, -1, true)
	_text(Vector2(297, 49), "LIVE SESSION", _mono, 12, MUTE)
	var pause_rect := _pause_rect()
	var paused_hover := pause_rect.has_point(_mouse_at)
	draw_rect(pause_rect, Color("#2b3330") if paused_hover else Color("#202523"))
	draw_rect(pause_rect, LINE, false, 1.0)
	for x in [1103, 1108]:
		draw_rect(Rect2(x, 40, 2.5, 14), PAPER)
	_text(Vector2(1125, 52), "Pause", _display, 24 if _touch_layout else 17, PAPER)
	if not _touch_layout:
		_text(Vector2(1191, 51), "ESC", _mono, 11, MUTE)
	var title_x := 45.0
	if _cover:
		draw_texture_rect(_cover, Rect2(45, 115, 86, 86), false)
		draw_rect(Rect2(45, 115, 86, 86), Color(PAPER, 0.23), false, 1.0)
		title_x = 150.0
	_text(Vector2(title_x + 1, 128), "NOW PLAYING", _mono, 12, LIME)
	var title := str(_track.get("title", "")).to_upper()
	var title_size := 43
	while title_size > 24 and _headline.get_string_size(title, HORIZONTAL_ALIGNMENT_LEFT, -1, title_size).x > 484.0 - title_x:
		title_size -= 1
	_text(Vector2(title_x, 172), title, _headline, title_size, PAPER)
	_text(Vector2(title_x + 1, 197), str(_track.get("composer", "")), _display, 18, MUTE)
	_text(Vector2(1000, 138), Lanes.difficulty_name(_difficulty).to_upper(), _mono, 16, VIOLET, 235, HORIZONTAL_ALIGNMENT_RIGHT)
	_text(Vector2(1000, 164), "%s BPM" % int(_track.get("bpm", 120)), _mono, 13, MUTE, 235, HORIZONTAL_ALIGNMENT_RIGHT)
	_text(Vector2(44, 397), "SCORE", _mono, 12, MUTE)
	_text(Vector2(40, 447), _group_digits(_score()), _display, 41, PAPER)
	draw_line(Vector2(44, 470), Vector2(207, 470), LINE, 1.0)
	_text(Vector2(44, 500), "ACCURACY", _mono, 12, MUTE)
	var accuracy := "—" if _perfect + _good + _miss == 0 else "%.1f%%" % _accuracy()
	_text(Vector2(43, 537), accuracy, _display, 30, PAPER)
	_text(Vector2(1083, 397), "COMBO", _mono, 12, MUTE)
	_text(Vector2(1079, 447), "%d×" % _combo, _display, 41, LIME if _combo > 0 else PAPER)
	draw_line(Vector2(1083, 470), Vector2(1234, 470), LINE, 1.0)
	_text(Vector2(1083, 500), "BEST COMBO", _mono, 12, MUTE)
	_text(Vector2(1082, 537), "%d×" % _max_combo, _display, 30, PAPER)
	if _streak_time > 0.0:
		var alpha := 1.0 if _reduced else clampf(_streak_time / 0.3, 0.0, 1.0)
		draw_rect(Rect2(1083, 343, 151, 28), Color(LIME, 0.12 * alpha))
		draw_rect(Rect2(1083, 343, 3, 28), Color(LIME, alpha))
		_text(Vector2(1093, 362), "%d-NOTE STREAK" % _streak_count, _mono, 12, Color(LIME, alpha))
	if _feedback_time > 0 and _mode != Mode.COUNT_IN:
		var col := LIME if _feedback == "PERFECT" else VIOLET
		if _feedback == "MISS":
			col = Color("#ffa295")
		elif _feedback == "HOLD":
			col = PAPER
		var alpha := minf(_feedback_time / 0.14, 1.0)
		_text(Vector2(455, 146), _feedback, _headline, 40, Color(col, alpha), 370.0, HORIZONTAL_ALIGNMENT_CENTER)
		_text(Vector2(455, 167), _timing_feedback, _mono, 11, Color(PAPER, alpha * 0.82), 370.0, HORIZONTAL_ALIGNMENT_CENTER)
	for hand in range(0 if _touch_layout else 2):
		var left := _track_point(hand * Lanes.HAND_SPLIT, 0.0).x
		var right := _track_point((hand + 1) * Lanes.HAND_SPLIT, 0.0).x
		var mid := (left + right) * 0.5
		var spacing := 53.0
		var color: Color = Lanes.COLORS[3 if hand == 0 else 6]
		draw_line(Vector2(left + 2, 702), Vector2(mid - spacing, 702), Color(color, 0.29), 1.0)
		draw_line(Vector2(mid + spacing, 702), Vector2(right - 2, 702), Color(color, 0.29), 1.0)
		_text(Vector2(left, 706), "LEFT HAND" if hand == 0 else "RIGHT HAND", _mono, 10, MUTE, right - left, HORIZONTAL_ALIGNMENT_CENTER)
	var time := clampf(_song_time, 0.0, _duration)
	if not _touch_layout:
		draw_line(Vector2(45, 720), Vector2(1235, 720), LINE, 1.0)
	_text(Vector2(45, 761), _time_label(time), _mono, 16, PAPER)
	_text(Vector2(1172, 761), _time_label(_duration), _mono, 16, MUTE, 64, HORIZONTAL_ALIGNMENT_RIGHT)
	var ratio := clampf(time / maxf(_duration, 0.001), 0.0, 1.0)
	var bar := Rect2(119, 753, 1044, 3)
	draw_rect(bar, Color("#3b4140"))
	draw_rect(Rect2(bar.position, Vector2(bar.size.x * ratio, bar.size.y)), LIME)
	draw_circle(Vector2(bar.position.x + bar.size.x * ratio, bar.position.y + 1.5), 4.1, LIME, true, -1, true)

func _draw_count() -> void:
	# Keep the strike line visible while introducing the very first notes.
	var center := Vector2(640, 450)
	draw_circle(center, 55, Color("#151a1d"), true, -1, true)
	draw_arc(center, 54, 0.0, TAU, 82, LINE, 2.0, true)
	var fraction := clampf(_count / _beat - (ceili(_count / _beat) - 1), 0.001, 1.0)
	draw_arc(center, 54, -PI * 0.5, -PI * 0.5 + TAU * fraction, 70, LIME, 3.0, true)
	_text(Vector2(581, 470), str(maxi(1, ceili(_count / _beat))), _display, 57, PAPER, 118, HORIZONTAL_ALIGNMENT_CENTER)
	var prompt := "GET READY"
	if _returning:
		prompt = "RE-HOLD LIT LANES" if _active_hold.any(func(x: int) -> bool: return x >= 0) else "RESUMING"
	_text(Vector2(495, 535), prompt, _mono, 12, LIME, 290, HORIZONTAL_ALIGNMENT_CENTER)

func _draw_menu() -> void:
	draw_rect(Rect2(Vector2.ZERO, STAGE_SIZE), Color(0.025, 0.035, 0.04, 0.84))
	draw_rect(Rect2(413, 207, 454, 379), Color("#191e20"))
	draw_rect(Rect2(413, 207, 454, 379), Color("#58605b"), false, 1.0)
	draw_rect(Rect2(413, 207, 454, 3), LIME)
	if _mode == Mode.ERROR:
		_text(Vector2(447, 277), "Audio unavailable", _display, 35, PAPER)
		_text(Vector2(447, 319), str(_track.get("title", "")), _display, 20, MUTE)
		_menu_button(MENU_RECTS[1], "Back to library", true)
		return
	_text(Vector2(447, 251), "SESSION PAUSED", _mono, 12, LIME)
	_text(Vector2(446, 296), str(_track.get("title", "")), _display, 38, PAPER)
	_text(Vector2(448, 322), "%s   /   %s" % [Lanes.difficulty_name(_difficulty), _time_label(maxf(_song_time, 0.0))], _mono, 13, MUTE)
	for i in MENU_RECTS.size():
		_menu_button(MENU_RECTS[i], ["Resume", "Restart track", "Back to library"][i], _pause_choice == i)

func _menu_button(rect: Rect2, content: String, selected: bool) -> void:
	draw_rect(rect, LIME if selected else Color("#23292a"))
	if not selected:
		draw_rect(rect, LINE, false, 1.0)
	var color := INK if selected else PAPER
	_text(rect.position + Vector2(17, 34), content, _display, 22, color)
	var tip := rect.end - Vector2(22, rect.size.y * 0.5)
	draw_line(tip - Vector2(6, 5), tip, color, 1.5, true)
	draw_line(tip, tip + Vector2(-6, 5), color, 1.5, true)

func _time_label(seconds: float) -> String:
	var value := floori(maxf(seconds, 0.0))
	return "%d:%02d" % [floori(value / 60.0), value % 60]

func _group_digits(value: int) -> String:
	var raw := str(value)
	var grouped := ""
	for i in raw.length():
		if i > 0 and (raw.length() - i) % 3 == 0:
			grouped += ","
		grouped += raw[i]
	return grouped
