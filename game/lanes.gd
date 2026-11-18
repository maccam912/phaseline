extends RefCounted

const COUNT := 10
const HAND_SPLIT := 5
const KEYS := [KEY_A, KEY_S, KEY_D, KEY_F, KEY_G, KEY_H, KEY_J, KEY_K, KEY_L, KEY_SEMICOLON]
const COLORS := [
	Color("#a6d8ff"), Color("#6bd4da"), Color("#90e8ba"), Color("#c3fa68"), Color("#e5e995"),
	Color("#dcb8f7"), Color("#b7a8ff"), Color("#f5a9d0"), Color("#ffae95"), Color("#ffd38c")
]

static func key_name(physical_code: int) -> String:
	var code := physical_code
	if DisplayServer.get_name() != "headless":
		var localized := DisplayServer.keyboard_get_keycode_from_physical(physical_code)
		if localized != KEY_NONE:
			code = localized
	if (code >= 33 and code <= 126) or (code >= 160 and code <= 0x10ffff):
		return String.chr(code).to_upper()
	return OS.get_keycode_string(code).to_upper()

static func difficulty_name(id: String) -> String:
	return "Medium" if id == "normal" else id.capitalize()
