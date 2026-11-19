extends Control

const LIBRARY = preload("res://game/library.gd")
const PLAY = preload("res://game/play.gd")
const PANELS = preload("res://game/panels.gd")
const Preferences = preload("res://game/preferences.gd")
const DEFAULTS = Preferences.DEFAULTS
const SAVE_PATH = "user://phaseline.cfg"

var prefs: Dictionary = DEFAULTS.duplicate(true)
var records: Dictionary = {}
var tracks: Array
var selected := 0
var difficulty := "normal"
var active: Control
var preview := AudioStreamPlayer.new()
var preview_animation: Tween
var screen := ""
var config := ConfigFile.new()

func _ready() -> void:
	if not OS.has_feature("android"):
		get_window().min_size = Vector2i(800, 500)
	config.load(SAVE_PATH)
	var saved: Variant = config.get_value("player", "settings", {})
	if saved is Dictionary:
		for key in DEFAULTS:
			if saved.has(key) and typeof(saved[key]) == typeof(DEFAULTS[key]):
				prefs[key] = saved[key]
	prefs.keys = Preferences.lane_keys(prefs.keys)
	var saved_records: Variant = config.get_value("player", "home_row_records", {})
	if saved_records is Dictionary:
		records = saved_records
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://music/library.json"))
	if parsed is not Array or parsed.is_empty():
		var error_label := Label.new()
		error_label.text = "The soundtrack library could not be loaded."
		add_child(error_label)
		push_error(error_label.text)
		return
	tracks = parsed
	for index in tracks.size():
		if tracks[index].id == config.get_value("player", "track", ""):
			selected = index
	var saved_level: String = config.get_value("player", "difficulty", "normal")
	if saved_level in LIBRARY.LEVELS:
		difficulty = saved_level
	add_child(preview)
	preview.finished.connect(_preview_ended)
	_apply_display()
	_library()

func _save() -> void:
	config.set_value("player", "settings", prefs)
	config.set_value("player", "home_row_records", records)
	config.set_value("player", "track", tracks[selected].id)
	config.set_value("player", "difficulty", difficulty)
	if config.save(SAVE_PATH) != OK:
		push_warning("Could not save player preferences.")

func _apply_display() -> void:
	if DisplayServer.get_name() != "headless" and not OS.has_feature("android"):
		var mode := DisplayServer.WINDOW_MODE_FULLSCREEN if prefs.fullscreen else DisplayServer.WINDOW_MODE_WINDOWED
		var is_fullscreen := DisplayServer.window_get_mode() in [DisplayServer.WINDOW_MODE_FULLSCREEN, DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN]
		if is_fullscreen != bool(prefs.fullscreen):
			DisplayServer.window_set_mode(mode)

func _mount(view: Control, mode: String) -> void:
	_stop_preview()
	if is_instance_valid(active):
		remove_child(active)
		active.queue_free()
	active = view
	screen = mode
	add_child(active)
	active.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

func _library() -> void:
	var view := LIBRARY.new()
	_mount(view, "library")
	view.selection_changed.connect(_selected)
	view.difficulty_changed.connect(_difficulty_changed)
	view.play_requested.connect(_start)
	view.preview_requested.connect(_toggle_preview)
	view.panel_requested.connect(_panel)
	view.quit_requested.connect(get_tree().quit)
	view.setup(tracks, selected, difficulty, records, prefs)

func _selected(index: int) -> void:
	var was_previewing := preview.playing
	_stop_preview()
	selected = index
	_save()
	if was_previewing:
		_toggle_preview()

func _difficulty_changed(level: String) -> void:
	difficulty = level
	_save()

func _toggle_preview() -> void:
	if screen != "library":
		return
	if preview.playing:
		_stop_preview()
		return
	var track: Dictionary = tracks[selected]
	preview.stream = load(track.audio)
	if not preview.stream:
		return
	var start := float(track.get("preview", 0))
	var length := minf(18.0, preview.stream.get_length() - start)
	var volume := linear_to_db(maxf(0.0001, float(prefs.music_volume) * 0.85))
	preview.volume_db = -80.0
	preview.play(start)
	active.set_preview(true)
	preview_animation = create_tween()
	preview_animation.tween_property(preview, "volume_db", volume, 0.18)
	preview_animation.tween_interval(maxf(0, length - 0.8))
	preview_animation.tween_property(preview, "volume_db", -80, 0.62)
	preview_animation.tween_callback(_stop_preview)

func _preview_ended() -> void:
	_stop_preview()

func _stop_preview() -> void:
	if preview_animation:
		preview_animation.kill()
		preview_animation = null
	preview.stop()
	if is_instance_valid(active) and screen == "library":
		active.set_preview(false)

func _start() -> void:
	var view := PLAY.new()
	_mount(view, "play")
	view.finished.connect(_finished)
	view.exited.connect(_library)
	view.setup(tracks[selected], difficulty, prefs.duplicate(true))

func _finished(result: Dictionary) -> void:
	var key := "%s/%s" % [tracks[selected].id, difficulty]
	var score := int(result.score)
	var record := score > int(records.get(key, 0))
	if record or not records.has(key):
		records[key] = score
		_save()
	_panel("results", {"track": tracks[selected], "difficulty": difficulty, "result": result,
		"best": int(records.get(key, 0)), "is_record": record})

func _panel(mode: String, data: Dictionary = {}) -> void:
	var view := PANELS.new()
	_mount(view, mode)
	view.closed.connect(_library)
	view.settings_changed.connect(_settings_changed)
	view.replay_requested.connect(_start)
	view.setup(mode, data, prefs.duplicate(true))

func _settings_changed(updated: Dictionary) -> void:
	prefs = updated.duplicate(true)
	_apply_display()
	_save()

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		if screen == "library":
			get_tree().quit()
		elif is_instance_valid(active):
			active.call_deferred("go_back")
	elif what in [NOTIFICATION_APPLICATION_FOCUS_OUT, NOTIFICATION_APPLICATION_PAUSED] and screen == "library" and preview.playing:
		_stop_preview()
