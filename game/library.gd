extends Control

signal selection_changed(index: int)
signal difficulty_changed(level: String)
signal play_requested
signal preview_requested
signal panel_requested(mode: String)
signal quit_requested

const GLYPH = preload("res://game/glyph.gd")
const BODY = preload("res://assets/fonts/display.ttf")
const DISPLAY = preload("res://assets/fonts/headline.ttf")
const MONO = preload("res://assets/fonts/mono.ttf")
const BG := Color("#0e1012")
const PANEL := Color("#191c1f")
const LINE := Color("#33383b")
const WHITE := Color("#f1f3ee")
const MUTED := Color("#a2aaa9")
const DIM := Color("#868e90")
const LIME := Color("#c4f96c")
const Layout = preload("res://game/lanes.gd")
const LEVELS := ["easy", "normal", "hard", "expert"]
const LEFT_ART := Rect2(48,185,647,328)
const PREVIEW_RECT := Rect2(566,458,108,34)

var tracks: Array
var current := 0
var difficulty := "normal"
var records: Dictionary
var prefs: Dictionary
var covers: Array[Texture2D] = []
var italic := FontVariation.new()
var targets: Dictionary = {}
var hovered := ""
var keyboard_focus := false
var previewing := false
var animation_time := 0.0
var gradient := GradientTexture2D.new()
var left_shade := GradientTexture2D.new()
var shape_cache := {}

func setup(songs: Array, index: int, level: String, bests: Dictionary, settings: Dictionary) -> void:
	tracks = songs
	current = index
	difficulty = level
	records = bests
	prefs = settings
	italic.base_font = DISPLAY
	italic.variation_transform = Transform2D(Vector2(1, 0.13), Vector2(0, 1), Vector2.ZERO)
	for track in tracks:
		covers.append(load("res://assets/covers/%s.webp" % track.id))
	gradient = _gradient(Vector2(0,0.18), Vector2(0,1), PackedFloat32Array([0.0,0.40,0.74,1.0]),
		PackedColorArray([Color(0,0,0,0),Color(0.02,0.02,0.025,0.05),Color(0.024,0.021,0.03,0.68),Color(0.024,0.021,0.03,0.96)]))
	left_shade = _gradient(Vector2(0,0),Vector2(1,0),PackedFloat32Array([0.0,0.7,1.0]),
		PackedColorArray([Color(0.04,0.035,0.05,0.20),Color(0,0,0,0),Color(0,0,0,0)]))
	_target("arcade", Rect2(668,0,110,71), "Track select")
	_target("guide", Rect2(790,0,157,71), "How to play")
	_target("settings", Rect2(958,0,145,71), "Settings")
	_target("quit", Rect2(1186,14,46,43), "Quit game")
	_target("preview", PREVIEW_RECT, "Play or stop preview (Space)")
	for i in tracks.size():
		_target("track_%d" % i, _row_rect(i), "%s by %s" % [tracks[i].title, tracks[i].composer])
	for i in LEVELS.size():
		_target(LEVELS[i], Rect2(249+i*120,649,114,43), Layout.difficulty_name(LEVELS[i])+" difficulty")
	_target("start",Rect2(950,640,260,60),"Start track (Enter)")
	_target("credits",Rect2(1127,754,106,40),"Music and game credits")
	queue_redraw()

func _gradient(a: Vector2,b: Vector2,stops: PackedFloat32Array,colors: PackedColorArray) -> GradientTexture2D:
	var tex := GradientTexture2D.new()
	tex.width = 256
	tex.height = 256
	tex.fill_from = a
	tex.fill_to = b
	tex.gradient = Gradient.new()
	tex.gradient.offsets = stops
	tex.gradient.colors = colors
	return tex

func _row_rect(i: int) -> Rect2:
	return Rect2(719,222+i*76,513,69)

func _target(id: String, rect: Rect2, description: String) -> void:
	var button := Button.new()
	button.name = id
	button.position = rect.position
	button.size = rect.size
	button.tooltip_text = description
	button.accessibility_name = description
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	button.flat = true
	for state in ["normal","hover","pressed","focus","disabled","hover_pressed"]:
		button.add_theme_stylebox_override(state, StyleBoxEmpty.new())
	button.pressed.connect(_activate.bind(id))
	button.mouse_entered.connect(func(): hovered = id; queue_redraw())
	button.mouse_exited.connect(func(): hovered = ""; queue_redraw())
	button.focus_entered.connect(queue_redraw)
	button.focus_exited.connect(queue_redraw)
	add_child(button)
	targets[id] = button

func _activate(id: String) -> void:
	match id:
		"arcade": pass
		"guide", "settings", "credits": panel_requested.emit(id)
		"preview": preview_requested.emit()
		"quit": quit_requested.emit()
		"start": play_requested.emit()
		"easy", "normal", "hard", "expert":
			difficulty = id
			difficulty_changed.emit(id)
		_:
			if id.begins_with("track_"):
				_select(id.trim_prefix("track_").to_int())
	queue_redraw()

func _select(index: int) -> void:
	if index != current:
		current = index
		selection_changed.emit(current)
	queue_redraw()

func set_preview(value: bool) -> void:
	previewing = value
	queue_redraw()

func _process(delta: float) -> void:
	if previewing and not prefs.get("reduced_motion",false):
		animation_time += delta
		queue_redraw()

func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		keyboard_focus = false
	if not event is InputEventKey or not event.pressed or tracks.is_empty():
		return
	var viewport := get_viewport()
	var key := event.keycode as int
	if key == KEY_TAB:
		keyboard_focus = true
		queue_redraw()
		return
	if event.echo and key not in [KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT]:
		return
	match key:
		KEY_UP, KEY_DOWN:
			keyboard_focus = false
			_select(posmod(current + (-1 if key == KEY_UP else 1), tracks.size()))
		KEY_LEFT, KEY_RIGHT:
			keyboard_focus = false
			_activate(LEVELS[posmod(LEVELS.find(difficulty) + (-1 if key == KEY_LEFT else 1),LEVELS.size())])
		KEY_SPACE:
			preview_requested.emit()
		KEY_ENTER, KEY_KP_ENTER:
			var focused := get_viewport().gui_get_focus_owner()
			if keyboard_focus and focused and focused.get_parent() == self:
				_activate(str(focused.name))
			else:
				play_requested.emit()
		_:
			return
	viewport.set_input_as_handled()

func _draw() -> void:
	if tracks.is_empty():
		return
	var track: Dictionary = tracks[current]
	draw_rect(Rect2(0,0,1280,800), BG)
	_header()
	_section_heading()
	_hero(track)
	_setlist()
	_controls(track)
	_footer()
	if keyboard_focus:
		var focused := get_viewport().gui_get_focus_owner()
		if focused and focused.get_parent() == self:
			draw_rect(focused.get_rect().grow(2), WHITE, false, 1.6)

func _box(rect: Rect2, fill: Color, edge := Color.TRANSPARENT, radius := 4) -> void:
	var cache_key := "%s%s%d" % [fill.to_html(),edge.to_html(),radius]
	if not shape_cache.has(cache_key):
		var style := StyleBoxFlat.new()
		style.bg_color = fill
		style.border_color = edge
		style.set_border_width_all(1 if edge.a > 0 else 0)
		style.set_corner_radius_all(radius)
		shape_cache[cache_key] = style
	draw_style_box(shape_cache[cache_key],rect)

func _text(value: String, x: float, y: float, height: int, color: Color, font: Font = BODY, width := -1.0) -> void:
	draw_string(font,Vector2(x,y),value,HORIZONTAL_ALIGNMENT_LEFT,width,height,color)

func _right(value: String, x: float, y: float, height: int, color: Color, font: Font = MONO) -> void:
	_text(value, x-font.get_string_size(value,HORIZONTAL_ALIGNMENT_LEFT,-1,height).x,y,height,color,font)

func _small(value: String, x: float, y: float, color := MUTED, height := 12, spacing := 1.25) -> void:
	for letter in value:
		_text(letter,x,y,height,color,MONO)
		x += MONO.get_string_size(letter,HORIZONTAL_ALIGNMENT_LEFT,-1,height).x+spacing

func _icon(icon: String,x: float,y: float,s: float,color: Color) -> void:
	GLYPH.draw(self,icon,Vector2(x,y),s,color)

func _hot(id: String) -> bool:
	return hovered == id or (keyboard_focus and targets.has(id) and targets[id].has_focus())

func _header() -> void:
	draw_rect(Rect2(0,0,1280,71),Color("#141618"))
	draw_line(Vector2(0,71),Vector2(1280,71),LINE)
	_icon("brand",48,12,45,LIME)
	_text("PHASELINE",108,47,32,WHITE,italic)
	for nav in [["arcade","disc","Arcade",685],["guide","help","How to play",808],["settings","gear","Settings",975]]:
		var selected: bool = nav[0] == "arcade"
		var color := LIME if selected else (WHITE if _hot(nav[0]) else MUTED)
		_icon(nav[1],nav[3],26,20,color)
		_text(nav[2],nav[3]+27,42,18,color)
		if selected:
			draw_rect(Rect2(nav[3]-5,68,91,3),LIME)
	draw_line(Vector2(1165,24),Vector2(1165,47),LINE)
	_icon("exit",1198,24,23,WHITE if _hot("quit") else MUTED)

func _section_heading() -> void:
	draw_rect(Rect2(49,97,22,3),LIME)
	_small("SINGLE PLAYER",80,103,LIME,11,1.4)
	_text("TRACK SELECT",48,159,64,WHITE,italic)
	_icon("disc",1018,111,38,Color("#9a89b2"))
	_small("COLLECTION  01",1072,124,DIM,10,1.3)
	_text("Classical Reworks",1071,150,21,WHITE)

func _cover(index: int, rect: Rect2, vertical_anchor := 0.5) -> void:
	var texture := covers[index]
	if texture == null:
		draw_rect(rect,PANEL)
		return
	var src_size := texture.get_size()
	var ratio := maxf(rect.size.x/src_size.x,rect.size.y/src_size.y)
	var crop := rect.size/ratio
	var offset := (src_size-crop)*Vector2(0.5,vertical_anchor)
	draw_texture_rect_region(texture,rect,Rect2(offset,crop))

func _time(seconds: float) -> String:
	var whole := roundi(seconds)
	return "%d:%02d" % [floori(whole/60.0),whole%60]

func _hero(track: Dictionary) -> void:
	_cover(current,LEFT_ART,0.35)
	draw_texture_rect(left_shade,LEFT_ART,false)
	draw_texture_rect(gradient,LEFT_ART,false)
	draw_rect(LEFT_ART,Color(1,1,1,0.13),false,1)
	var tag := str(track.genre).to_upper()
	var tag_width := 30.0 + MONO.get_string_size(tag,HORIZONTAL_ALIGNMENT_LEFT,-1,11).x + tag.length()
	_box(Rect2(68,204,tag_width,24),Color("#101215e8"),Color("#ffffff40"),2)
	draw_circle(Vector2(80,216),2.7,LIME,true,-1,true)
	_small(tag,89,220,WHITE,11,1)
	_small("TRACK  /  %02d" % (current+1),72,406,LIME,11,1.3)
	_text(str(track.title).to_upper(),68,460,62,WHITE,italic,588)
	var sub := "%s  /  %s" % [track.composer,track.get("work","")]
	_text(sub,71,488,18,Color("#e0e1e2"),BODY,476)
	_box(PREVIEW_RECT,Color("#c6f76c") if previewing else (Color("#3c4143") if _hot("preview") else Color("#14171be8")),Color("#b1b7b690"),4)
	var fg := BG if previewing else WHITE
	_icon("pause" if previewing else "headphones",574,466,18,fg)
	_text("Stop" if previewing else "Preview",598,481,16,fg)
	_box(Rect2(48,513,647,82),PANEL,LINE,0)
	var score_key := "%s/%s" % [track.id,difficulty]
	var best := _format_score(int(records[score_key])) if records.has(score_key) else "—"
	for stat in [["bpm","TEMPO","%d BPM" % track.bpm,68],["clock","LENGTH",_time(track.duration),277],["best","PERSONAL BEST",best,482]]:
		var x: int = stat[3]
		_icon(stat[0],x,530,15,DIM)
		_small(stat[1],x+21,542,MUTED,10,1.15)
		_text(stat[2],x,574,24,WHITE)
	for x in [253,458]:
		draw_line(Vector2(x,533),Vector2(x,576),LINE)

func _format_score(score: int) -> String:
	var value := str(score)
	var index := value.length()-3
	while index > 0:
		value = value.insert(index,",")
		index -= 3
	return value

func _setlist() -> void:
	_icon("stack",718,184,23,LIME)
	_small("SETLIST",751,201,WHITE,14,1.1)
	_right("%02d TRACKS" % tracks.size(),1230,201,12,DIM)
	for i in tracks.size():
		var rect := _row_rect(i)
		var y := rect.position.y
		var chosen := i == current
		var hot := _hot("track_%d" % i)
		_box(rect,(Color("#262d20") if chosen else (Color("#24282b") if hot else PANEL)),LIME if chosen else LINE,5)
		if chosen:
			draw_rect(Rect2(rect.position.x+1,y+12,3,45),LIME)
		_cover(i, Rect2(730,y+8,57,53))
		_text(str(tracks[i].title),803,y+32,23,LIME if chosen else WHITE)
		_text(str(tracks[i].composer),804,y+53,15,MUTED)
		_right(_time(tracks[i].duration),1192,y+39,14,Color("#c8ccca"))
		if chosen:
			for bar in 3:
				var h := 6.0 + ((bar+1)*4)%11
				if previewing and not prefs.get("reduced_motion",false):
					h += sin(animation_time*8.0+bar*1.7)*4
				draw_rect(Rect2(1205+bar*4,y+34-h/2.0,2.5,h),LIME)
		else:
			_icon("chevron",1205,y+26,15,DIM)

func _controls(track: Dictionary) -> void:
	_box(Rect2(48,620,1184,102),Color("#171a1c"),LINE,5)
	_icon("sliders",69,648,20,LIME)
	_small("DIFFICULTY",98,664,WHITE,12,1.1)
	var notes: Array = track.charts[difficulty]
	_text("%d notes" % notes.size(),98,690,16,MUTED)
	for i in LEVELS.size():
		var name_id: String = LEVELS[i]
		var rect := Rect2(249+i*120,649,114,43)
		var selected := name_id == difficulty
		var col := LIME if selected else MUTED
		_box(rect,Color("#2b3324") if selected else (Color("#292d30") if _hot(name_id) else Color("#1d2023")),Color("#859c65") if selected else LINE,4)
		for j in LEVELS.size():
			var height := 4 + j*3
			draw_rect(Rect2(rect.position.x+11+j*4,677-height,2.7,height),col if j<=i else Color("#4e5552"))
		_text(Layout.difficulty_name(name_id),rect.position.x+36,676,17,col)
	_box(Rect2(950,640,260,60),Color("#d7ff91") if _hot("start") else LIME,Color.TRANSPARENT,4)
	_icon("play",971,656,27,BG)
	_text("START TRACK",1010,678,25,BG,italic)
	_box(Rect2(1154,658,39,23),Color("#00000008"), Color("#1a250e66"),3)
	_text("ENT",1163,674,11,BG,MONO)

func _keycap(value: String,x: float,y: float,width: float) -> void:
	_box(Rect2(x,y,width,22),Color("#1d2022"),Color("#393e40"),3)
	var w := MONO.get_string_size(value,HORIZONTAL_ALIGNMENT_LEFT,-1,11).x
	_text(value,x+(width-w)/2,y+15,11,Color("#d7dbd5"),MONO)

func _footer() -> void:
	draw_line(Vector2(48,751),Vector2(1232,751),LINE)
	_keycap("↑",48,766,22)
	_keycap("↓",74,766,22)
	_text("Browse",106,782,15,MUTED)
	_keycap("←",182,766,22)
	_keycap("→",208,766,22)
	_text("Difficulty",240,782,15,MUTED)
	_keycap("SPACE",329,766,48)
	_text("Preview",387,782,15,MUTED)
	_icon("music",1142,765,19,WHITE if _hot("credits") else DIM)
	_text("Credits",1170,782,16,WHITE if _hot("credits") else MUTED)
