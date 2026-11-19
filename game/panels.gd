extends Control

signal closed
signal settings_changed(new_settings: Dictionary)
signal replay_requested

const Art := preload("res://game/panel_art.gd")
const Calibration := preload("res://game/panel_calibration.gd")
const INK := Color("#0e1012")
const BAR := Color("#141618")
const CARD := Color("#191c1f")
const FIELD := Color("#232729")
const RULE := Color("#353a3c")
const TEXT := Color("#f1f3eb")
const MUTED := Color("#a4afa4")
const GREEN := Color("#c3fa68")
const LILAC := Color("#c8b3ed")
const Lanes := preload("res://game/lanes.gd")
const Preferences := preload("res://game/preferences.gd")
const DEFAULTS = Preferences.DEFAULTS

var mode := ""
var payload: Dictionary
var prefs: Dictionary
var display_font: Font
var mono_font: Font
var body_font: Font
var italic := FontVariation.new()
var _shell: VBoxContainer
var _body: VBoxContainer
var _outer: MarginContainer
var _top_inset: MarginContainer
var _columns: Array[BoxContainer] = []
var _binding := -1
var _binding_labels: Array[Button] = []
var _binding_hint: Label
var _credits_from_guide := false
var _cal: Calibration
var _cal_status: Label
var _cal_tip: Label
var _cal_apply: Button
var _cal_tap: Button
var _tap_plot: Art
var _focus_start: Control
var _touch_layout := OS.has_feature("android")

func setup(next_mode: String, data: Dictionary, settings: Dictionary) -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	payload = data
	prefs = DEFAULTS.duplicate(true)
	prefs.merge(settings, true)
	prefs.keys = Preferences.lane_keys(prefs.keys)
	if ResourceLoader.exists("res://assets/fonts/headline.ttf"):
		display_font = load("res://assets/fonts/headline.ttf")
	if ResourceLoader.exists("res://assets/fonts/mono.ttf"):
		mono_font = load("res://assets/fonts/mono.ttf")
	if ResourceLoader.exists("res://assets/fonts/display.ttf"):
		body_font = load("res://assets/fonts/display.ttf")
	else:
		body_font = ThemeDB.fallback_font
	display_font = display_font if display_font else body_font
	mono_font = mono_font if mono_font else body_font
	italic.base_font = display_font
	italic.variation_transform = Transform2D(Vector2(1, 0), Vector2(-0.13, 1), Vector2.ZERO)
	_open(next_mode)
	if not resized.is_connected(_layout):
		resized.connect(_layout)

func _open(next_mode: String) -> void:
	if is_instance_valid(_cal):
		_cal.stop()
		_cal = null
	for child in get_children():
		remove_child(child)
		child.queue_free()
	_columns.clear()
	_binding_labels.clear()
	_binding = -1
	_focus_start = null
	mode = next_mode
	var backdrop := ColorRect.new()
	backdrop.color = INK
	backdrop.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(backdrop)
	backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_shell = _vbox(0)
	add_child(_shell)
	_shell.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var top_bg := PanelContainer.new()
	top_bg.add_theme_stylebox_override("panel", _style(BAR, Color.TRANSPARENT, 0))
	_shell.add_child(top_bg)
	_top_inset = _inset(50, 14, 50, 14)
	top_bg.add_child(_top_inset)
	var header := _hbox(13)
	_top_inset.add_child(header)
	var icon := Art.new()
	icon.mode = "brand"
	icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	icon.custom_minimum_size = Vector2(45, 42)
	header.add_child(icon)
	var logo := _label(header, "PHASELINE", 32, TEXT, italic)
	logo.vertical_alignment = VERTICAL_ALIGNMENT_CENTER

	_spacer(header)
	var back_text := "←  Settings" if mode == "calibration" else ("←  Player guide" if mode == "credits" and _credits_from_guide else "←  Library")
	var back := _button(header, back_text, go_back)
	_focus_start = back
	_line(_shell)
	var scroll := ScrollContainer.new()
	scroll.follow_focus = true
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_shell.add_child(scroll)
	_outer = _inset(50, 32, 50, 32)
	_outer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(_outer)
	_body = _vbox(23)
	_outer.add_child(_body)
	match mode:
		"settings": _settings()
		"guide": _guide()
		"credits": _credits()
		"results": _results()
		"calibration": _calibration()
	_layout()
	_focus_default.call_deferred()

func _focus_default() -> void:
	if is_instance_valid(_focus_start) and _focus_start.is_inside_tree():
		_focus_start.grab_focus()

func _layout() -> void:
	if not is_instance_valid(_outer):
		return
	var margin := int(maxf(22.0, (size.x - minf(1184.0, size.x * 0.925)) * 0.5))
	for side in ["margin_left", "margin_right"]:
		_outer.add_theme_constant_override(side, margin)
		_top_inset.add_theme_constant_override(side, margin)
	for row in _columns:
		row.vertical = size.x < 880

func go_back() -> void:
	if _binding != -1:
		_cancel_binding()
	elif mode == "calibration":
		_open("settings")
	elif mode == "credits" and _credits_from_guide:
		_credits_from_guide = false
		_open("guide")
	else:
		closed.emit()

func _input(event: InputEvent) -> void:
	if not is_visible_in_tree() or mode.is_empty():
		return
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_ESCAPE:
			get_viewport().set_input_as_handled()
			go_back()
		elif _binding >= 0:
			get_viewport().set_input_as_handled()
			_accept_binding(event)
		elif mode == "calibration" and event.physical_keycode == KEY_SPACE:
			get_viewport().set_input_as_handled()
			_calibration_tap()

func _title(kicker: String, heading: String, description := "") -> void:
	var stack := _vbox(5)
	_body.add_child(stack)
	if not kicker.is_empty():
		_label(stack, kicker, 12, GREEN, mono_font)
	_label(stack, heading.to_upper(), 58, TEXT, italic, true)
	if not description.is_empty():
		_label(stack, description, 17, MUTED, body_font, true)

func _settings() -> void:
	_title("", "Settings")
	var row := _columns_row()
	var audio_card := _card(row)
	_card_heading(audio_card, "Audio & timing")
	_slider_setting(audio_card, "Music volume", "music_volume", 0, 100, true)
	_slider_setting(audio_card, "Hit sounds", "sfx_volume", 0, 100, true)
	_line(audio_card)
	_slider_setting(audio_card, "Timing offset", "offset_ms", -250, 250, false)
	_label(audio_card, "Positive values move the hit window later.", 14, MUTED, body_font, true)
	var cal_row := _hbox(10)
	audio_card.add_child(cal_row)
	_button(cal_row, "Calibrate timing", func(): _open("calibration"))
	var controls_card := _card(row)
	_card_heading(controls_card, "Controls & display")
	if _touch_layout:
		_label(controls_card, "Tap a numbered pad to play its lane. For chords, touch all the matching pads together.", 18, MUTED, body_font, true)
	else:
		_keyboard_settings(controls_card)
		_toggle_setting(controls_card, "Fullscreen", "fullscreen")
	_toggle_setting(controls_card, "Reduced motion", "reduced_motion")
	var actions := _hbox(10)
	_body.add_child(actions)
	_spacer(actions)
	_button(actions, "Restore defaults", _restore_defaults)

func _keyboard_settings(controls_card: Control) -> void:
	for hand in range(2):
		var hand_group := _vbox(6)
		controls_card.add_child(hand_group)
		_label(hand_group, "LEFT HAND" if hand == 0 else "RIGHT HAND", 11, LILAC, mono_font)
		var keys_row := _hbox(7)
		hand_group.add_child(keys_row)
		for index in range(Lanes.HAND_SPLIT):
			var lane := hand * Lanes.HAND_SPLIT + index
			var key_stack := _vbox(3)
			key_stack.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			keys_row.add_child(key_stack)
			var key := _button(key_stack, Lanes.key_name(prefs.keys[lane]), _start_binding.bind(lane))
			key.custom_minimum_size.y = 37
			key.add_theme_font_override("font", mono_font)
			key.add_theme_color_override("font_color", Lanes.COLORS[lane])
			key.accessibility_name = "Rebind lane %d" % (lane + 1)
			_binding_labels.append(key)
			var lane_label := _label(key_stack, "LANE %d" % (lane + 1), 10, MUTED, mono_font)
			lane_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_binding_hint = _label(controls_card, "Select a key to rebind its lane.", 14, MUTED, body_font, true)
	_line(controls_card)

func _slider_setting(parent: Control, caption: String, key: String, lo: int, hi: int, percent: bool) -> void:
	var stack := _vbox(7)
	parent.add_child(stack)
	var heading := _hbox(8)
	stack.add_child(heading)
	_label(heading, caption, 16, TEXT, body_font)
	_spacer(heading)
	var val := roundi(float(prefs[key]) * (100.0 if percent else 1.0))
	var readout := _label(heading, _format_slider(val, percent), 14, GREEN, mono_font)
	var slider := HSlider.new()
	slider.min_value = lo
	slider.max_value = hi
	slider.step = 1
	slider.value = val
	slider.scrollable = false
	slider.custom_minimum_size.y = 48 if _touch_layout else 20
	slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var groove := _style(FIELD, Color.TRANSPARENT, 3)
	groove.content_margin_top = 3
	groove.content_margin_bottom = 3
	slider.add_theme_stylebox_override("slider", groove)
	slider.add_theme_stylebox_override("grabber_area", _style(GREEN, Color.TRANSPARENT, 3))
	slider.add_theme_stylebox_override("grabber_area_highlight", _style(LILAC, Color.TRANSPARENT, 3))
	slider.add_theme_stylebox_override("focus", _outline())
	slider.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	slider.accessibility_name = caption
	stack.add_child(slider)
	slider.value_changed.connect(func(v: float):
		readout.text = _format_slider(roundi(v), percent)
		_set_pref(key, v / 100.0 if percent else roundi(v))
	)

func _format_slider(value: int, percent: bool) -> String:
	if percent:
		return "%d%%" % value
	return ("%+d ms" if value != 0 else "%d ms") % value

func _toggle_setting(parent: Control, caption: String, key: String) -> void:
	var row := _hbox(8)
	parent.add_child(row)
	_label(row, caption, 16, TEXT, body_font)
	_spacer(row)
	var button := _button(row, "", Callable())
	button.custom_minimum_size.x = 70
	button.toggle_mode = true
	button.button_pressed = prefs[key]
	button.accessibility_name = caption
	button.add_theme_stylebox_override("pressed", _styled_button(Color("#344329"), Color("#637d48")))
	var refresh := func(active: bool):
		button.text = "●  ON" if active else "○  OFF"
		button.add_theme_color_override("font_color", GREEN if active else MUTED)
	refresh.call(button.button_pressed)
	button.toggled.connect(func(active: bool):
		refresh.call(active)
		_set_pref(key, active)
	)

func _set_pref(key: String, value: Variant) -> void:
	prefs[key] = value
	settings_changed.emit(prefs.duplicate(true))

func _restore_defaults() -> void:
	prefs.merge(DEFAULTS.duplicate(true), true)
	settings_changed.emit(prefs.duplicate(true))
	_open("settings")

func _start_binding(lane: int) -> void:
	_cancel_binding()
	_binding = lane
	_binding_labels[lane].text = "…"
	_binding_hint.text = "Press a letter, number or punctuation key. Esc cancels."

func _cancel_binding() -> void:
	if _binding >= 0:
		_binding_labels[_binding].text = Lanes.key_name(prefs.keys[_binding])
		_binding_hint.text = "Select a key to rebind its lane."
		_binding = -1

func _accept_binding(event: InputEventKey) -> void:
	var code := event.physical_keycode
	if code < KEY_EXCLAM or code > KEY_ASCIITILDE or event.ctrl_pressed or event.alt_pressed or event.meta_pressed:
		_binding_hint.text = "Choose a letter, number or punctuation key."
		return
	var existing: int = prefs.keys.find(code)
	if existing != -1 and existing != _binding:
		_binding_hint.text = "%s is assigned to lane %d. Choose another key." % [Lanes.key_name(code), existing + 1]
		return
	var replacement: Array = prefs.keys.duplicate()
	replacement[_binding] = code
	_set_pref("keys", replacement)
	_cancel_binding()

func _guide() -> void:
	_title("", "How to play", "Play each note as it reaches the bright hit line.")
	var row := _columns_row()
	var preview := _card(row)
	_card_heading(preview, "Touch pads" if _touch_layout else "Hand position")
	var art := Art.new()
	art.mode = "guide"
	art.keys = range(1, Lanes.COUNT + 1).map(func(lane: int) -> String: return str(lane)) if _touch_layout else prefs.keys.map(Lanes.key_name)
	art.mono_font = mono_font
	art.mouse_filter = Control.MOUSE_FILTER_IGNORE
	art.custom_minimum_size.y = 186
	preview.add_child(art)
	if _touch_layout:
		_label(preview, "Each pad plays the lane directly above it. For chords, use a separate finger on each pad.", 17, MUTED, body_font, true)
	else:
		var home: Array = prefs.keys.map(Lanes.key_name)
		_label(preview, "Rest your index fingers on %s and %s. Reach inward from %s to %s with the left index, and from %s to %s with the right. Each index plays one key at a time." % [home[3], home[6], home[3], home[4], home[6], home[5]], 15, MUTED, body_font, true)
	var how := _card(row)
	_card_heading(how, "Tap, hold, release")
	_guide_item(how, "TAP", "Tap the matching pad when the note reaches the line." if _touch_layout else "Press the matching lane key when the head of a note reaches the line.")
	_guide_item(how, "HOLD", "For long notes, keep pressing until the tail reaches the line.")
	_guide_item(how, "PAUSE", "Tap Pause to resume later, restart, or return to the library." if _touch_layout else "Press Esc to pause, restart the track, or return to the library.")
	_guide_item(how, "TIMING", "If your hits consistently land early or late, use Calibrate timing in Settings.")
	var details := _columns_row()
	var levels := _card(details)
	_card_heading(levels, "Difficulty")
	for level in [["easy", "One note at a time, with room to find the next lane."], ["normal", "Up to two notes at once, including holds."], ["hard", "Denser rhythms and quicker changes, still capped at two."], ["expert", "Multi-finger chords. Up to eight notes at once, including holds."]]:
		var level_row := _hbox(10)
		levels.add_child(level_row)
		var name_label := _label(level_row, Lanes.difficulty_name(level[0]).to_upper(), 11, LILAC, mono_font)
		name_label.custom_minimum_size.x = 61
		var text_label := _label(level_row, level[1], 15, TEXT, body_font, true)
		text_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var scoring := _card(details)
	_card_heading(scoring, "Scoring")
	_label(scoring, "Perfect hits earn full credit within 65 ms. Good hits earn 65% credit within 145 ms. Each miss breaks your combo. A perfect run scores 1,000,000.", 16, MUTED, body_font, true)
	var actions := _hbox(10)
	_body.add_child(actions)
	_button(actions, "Music credits", func():
		_credits_from_guide = true
		_open("credits")
	)

func _guide_item(parent: Control, name_text: String, description: String) -> void:
	var column := _vbox(4)
	parent.add_child(column)
	_label(column, name_text, 11, LILAC, mono_font)
	_label(column, description, 16, TEXT, body_font, true)

func _credits() -> void:
	_title("", "Credits")
	var box := _card(_body)
	_card_heading(box, "Soundtrack")
	var records: Array = payload.get("tracks", [])
	if records.is_empty() and FileAccess.file_exists("res://music/library.json"):
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://music/library.json"))
		if parsed is Array:
			records = parsed
	for i in range(records.size()):
		var track: Dictionary = records[i]
		var entry := _hbox(16)
		box.add_child(entry)
		var words := _vbox(4)
		words.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		entry.add_child(words)
		_label(words, str(track.get("title", "")), 22, TEXT, display_font, true)
		_label(words, "%s  ·  %s" % [track.get("composer", ""), track.get("work", "")], 15, MUTED, body_font, true)
		var url := str(track.get("source", ""))
		if url.begins_with("https://"):
			_button(entry, "Composition source ↗", _open_source.bind(url))
		if i + 1 < records.size():
			_line(box)
	var rights := _card(_body)
	_card_heading(rights, "Recording & arrangement rights")
	_label(rights, "The source compositions are in the U.S. public domain. Phaseline’s original arrangements and note charts are available under CC0 1.0. The finished recordings include Apple instrument and drum sounds used under Apple’s royalty-free soundtrack license. Apple and its licensors retain rights to their source sounds.", 16, MUTED, body_font, true)
	var rights_row := _hbox(8)
	rights.add_child(rights_row)
	_button(rights_row, "Apple soundtrack terms ↗", _open_source.bind("https://support.apple.com/en-us/101908"))
	_button(rights_row, "Read CC0 1.0 ↗", _open_source.bind("https://creativecommons.org/publicdomain/zero/1.0/"))

	var tech := _card(_body)
	_card_heading(tech, "Engine & type")
	_label(tech, "Made with Godot Engine (MIT). Barlow, Barlow Condensed and Geist Mono are licensed under the SIL Open Font License. Full notices are bundled with the game.", 16, MUTED, body_font, true)
	var tech_row := _hbox(8)
	tech.add_child(tech_row)
	_button(tech_row, "Godot license ↗", _open_source.bind("https://godotengine.org/license/"))

func _open_source(url: String) -> void:
	OS.shell_open(url)

func _results() -> void:
	var track: Dictionary = payload.get("track", {})
	var result: Dictionary = payload.get("result", {})
	var difficulty := Lanes.difficulty_name(payload.get("difficulty", "normal")).to_upper()
	_title("SESSION COMPLETE", str(track.get("title", "Track complete")), "%s  /  %s" % [track.get("composer", ""), difficulty])
	var row := _columns_row()
	var grade_card := _card(row)
	grade_card.get_parent().size_flags_stretch_ratio = 0.74
	_label(grade_card, "PERFORMANCE GRADE", 12, LILAC, mono_font)
	var grade := Art.new()
	grade.mode = "grade"
	grade.grade = str(result.get("grade", "—"))
	grade.display_font = display_font
	grade.custom_minimum_size.y = 209
	grade.size_flags_vertical = Control.SIZE_EXPAND_FILL
	grade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	grade_card.add_child(grade)
	var stats := _card(row)
	stats.get_parent().size_flags_stretch_ratio = 1.26
	var line := _hbox(6)
	stats.add_child(line)
	_label(line, "FINAL SCORE", 12, MUTED, mono_font)
	_spacer(line)
	_label(line, "NEW BEST" if payload.get("is_record", false) else "PERSONAL BEST  %s" % _number(payload.get("best", 0)), 12, GREEN, mono_font)
	_label(stats, _number(result.get("score", 0)), 57, TEXT, display_font)
	_line(stats)
	var metrics := _hbox(12)
	stats.add_child(metrics)
	_metric(metrics, "ACCURACY", "%.1f%%" % float(result.get("accuracy", 0)))
	_metric(metrics, "MAX COMBO", "%d" % int(result.get("max_combo", 0)))
	_line(stats)
	var judgments := _hbox(7)
	stats.add_child(judgments)
	for item in [["PERFECT", "perfect", GREEN], ["GOOD", "good", LILAC], ["MISS", "miss", MUTED]]:
		var stat := _vbox(4)
		stat.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		judgments.add_child(stat)
		_label(stat, item[0], 11, item[2], mono_font)
		_label(stat, str(int(result.get(item[1], 0))), 22, TEXT, display_font)
	var actions := _hbox(10)
	_body.add_child(actions)
	_focus_start = _button(actions, "Play again", func(): replay_requested.emit(), true)
	_button(actions, "Back to library", func(): closed.emit())

func _metric(parent: Control, caption: String, val: String) -> void:
	var col := _vbox(5)
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	parent.add_child(col)
	_label(col, caption, 11, MUTED, mono_font)
	_label(col, val, 28, TEXT, display_font)

func _number(value: int) -> String:
	var digits := str(value)
	var index := digits.length() - 3
	while index > 0:
		digits = digits.insert(index, ",")
		index -= 3
	return digits

func _calibration() -> void:
	_title("", "Calibrate timing", "Listen to the click and tap the button in time with eight beats." if _touch_layout else "Listen to the click and tap Space in time with eight beats.")
	var box := _card(_body)
	_cal_status = _label(box, "0 / 8", 64, TEXT, display_font)
	_tap_plot = Art.new()
	_tap_plot.mode = "offset"
	_tap_plot.mono_font = mono_font
	_tap_plot.custom_minimum_size.y = 86
	_tap_plot.mouse_filter = Control.MOUSE_FILTER_IGNORE
	box.add_child(_tap_plot)
	_cal_tip = _label(box, "Join the beat whenever you are ready.", 17, MUTED, body_font, true)
	var buttons := _hbox(10)
	box.add_child(buttons)
	_cal_tap = _button(buttons, "Tap to the beat", Callable(), true)
	# Score pointer presses on contact. Keyboard Space is sampled in _input.
	_cal_tap.button_down.connect(_calibration_tap)
	_cal_apply = _button(buttons, "Apply offset", _apply_calibration)
	_cal_apply.disabled = true
	_button(buttons, "Start over", _start_calibration)
	_focus_start = _cal_tap
	_cal = Calibration.new()
	add_child(_cal)
	_cal.finished.connect(_start_calibration)
	_start_calibration()

func _start_calibration() -> void:
	_cal_status.text = "0 / 8"
	_cal_status.add_theme_color_override("font_color", TEXT)
	_cal_apply.disabled = true
	_cal_tap.disabled = false
	if float(prefs.music_volume) <= 0.0:
		_cal_tip.text = "Music volume is muted. Turn it up in Settings to hear the clicks."
		_cal_tap.disabled = true
		return
	_cal_tip.text = "Join the beat whenever you are ready."
	_tap_plot.offsets = []
	_tap_plot.queue_redraw()
	_cal.begin(prefs.music_volume)

func _calibration_tap() -> void:
	if not is_instance_valid(_cal) or not _cal.take_tap():
		return
	_tap_plot.offsets = _cal.samples.duplicate()
	_tap_plot.queue_redraw()
	var count: int = _cal.samples.size()
	if count == Calibration.TOTAL:
		_cal_status.text = _format_slider(_cal.measured_offset(), false)
		_cal_status.add_theme_color_override("font_color", GREEN)
		_cal_tip.text = "Measured across eight beats. Apply this offset or try another pass."
		_cal_tap.disabled = true
		_cal_apply.disabled = false
		_cal_apply.grab_focus()
	else:
		_cal_status.text = "%d / %d" % [count, Calibration.TOTAL]
		_cal_tip.text = "Keep tapping with the clicks."

func _apply_calibration() -> void:
	if is_instance_valid(_cal) and _cal.samples.size() == Calibration.TOTAL:
		_set_pref("offset_ms", _cal.measured_offset())
		_open("settings")

func _columns_row() -> BoxContainer:
	var row := BoxContainer.new()
	row.add_theme_constant_override("separation", 16)
	row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_body.add_child(row)
	_columns.append(row)
	return row

func _card(parent: Control) -> VBoxContainer:
	var panel := PanelContainer.new()
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var style := _style(CARD, RULE, 7)
	style.content_margin_left = 23
	style.content_margin_right = 23
	style.content_margin_top = 20
	style.content_margin_bottom = 22
	panel.add_theme_stylebox_override("panel", style)
	parent.add_child(panel)
	var inner := _vbox(14)
	panel.add_child(inner)
	return inner

func _card_heading(parent: Control, content: String) -> Label:
	return _label(parent, content, 24, TEXT, display_font, true)

func _label(parent: Control, content: String, point_size: int, tint: Color, face: Font, wrap := false) -> Label:
	var label := Label.new()
	label.text = content
	label.add_theme_font_override("font", face)
	label.add_theme_font_size_override("font_size", point_size)
	label.add_theme_color_override("font_color", tint)
	if wrap:
		label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(label)
	return label

func _button(parent: Control, caption: String, action: Callable, primary := false) -> Button:
	var button := Button.new()
	button.text = caption
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	button.custom_minimum_size.y = 58 if _touch_layout else 36
	button.add_theme_font_override("font", body_font)
	button.add_theme_font_size_override("font_size", 16)
	button.add_theme_stylebox_override("normal", _styled_button(GREEN if primary else FIELD, GREEN if primary else RULE))
	button.add_theme_stylebox_override("hover", _styled_button(Color("#dcffa2") if primary else Color("#2d352e"), GREEN if primary else MUTED))
	button.add_theme_stylebox_override("pressed", _styled_button(LILAC if primary else Color("#3a423a"), LILAC))
	button.add_theme_stylebox_override("disabled", _styled_button(BAR, RULE))
	button.add_theme_stylebox_override("focus", _outline())
	var text_color := INK if primary else TEXT
	for key in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color", "font_hover_pressed_color"]:
		button.add_theme_color_override(key, text_color)
	button.add_theme_color_override("font_disabled_color", Color("#727b72"))
	if action.is_valid():
		button.pressed.connect(action)
	parent.add_child(button)
	return button

func _style(fill: Color, border: Color, radius: int) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = fill
	box.set_corner_radius_all(radius)
	if border.a > 0.0:
		box.border_color = border
		box.set_border_width_all(1)
	return box

func _styled_button(fill: Color, border: Color) -> StyleBoxFlat:
	var button_style := _style(fill, border, 4)
	button_style.content_margin_left = 14
	button_style.content_margin_right = 14
	button_style.content_margin_top = 6
	button_style.content_margin_bottom = 6
	return button_style

func _outline() -> StyleBoxFlat:
	var focus := _style(Color.TRANSPARENT, LILAC, 6)
	focus.draw_center = false
	focus.set_border_width_all(2)
	focus.set_expand_margin_all(3)
	return focus

func _line(parent: Control) -> void:
	var line := ColorRect.new()
	line.color = RULE
	line.custom_minimum_size.y = 1
	line.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(line)

func _inset(left: int, top: int, right: int, bottom: int) -> MarginContainer:
	var inset := MarginContainer.new()
	inset.add_theme_constant_override("margin_left", left)
	inset.add_theme_constant_override("margin_top", top)
	inset.add_theme_constant_override("margin_right", right)
	inset.add_theme_constant_override("margin_bottom", bottom)
	return inset

func _spacer(parent: Control) -> void:
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	spacer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(spacer)

func _hbox(gap: int) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", gap)
	return row

func _vbox(gap: int) -> VBoxContainer:
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", gap)
	return column
