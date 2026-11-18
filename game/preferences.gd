extends RefCounted

const Layout = preload("res://game/lanes.gd")
const DEFAULTS = {
	"music_volume": 0.78, "sfx_volume": 0.6, "offset_ms": 0,
	"reduced_motion": false, "fullscreen": false, "keys": Layout.KEYS
}

static func lane_keys(stored: Variant) -> Array:
	var defaults := Layout.KEYS.duplicate()
	if stored is not Array or stored.size() not in [4, Layout.COUNT]:
		return defaults
	var used := {}
	for code in stored:
		if typeof(code) != TYPE_INT or code < KEY_EXCLAM or code > KEY_ASCIITILDE or used.has(code):
			return defaults
		used[code] = true
	if stored.size() == Layout.COUNT:
		return stored.duplicate()
	# Keep old D/F/J/K bindings on their corresponding lanes. Swap any displaced
	# home-row key onto the free lane, so all ten bindings remain distinct.
	var old_lanes := [2, 3, 6, 7]
	for i in old_lanes.size():
		var lane: int = old_lanes[i]
		var displaced := defaults.find(stored[i])
		if displaced >= 0:
			defaults[displaced] = defaults[lane]
		defaults[lane] = stored[i]
	return defaults
