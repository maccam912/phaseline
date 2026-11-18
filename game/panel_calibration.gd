extends AudioStreamPlayer

const BEAT := 0.6
const TOTAL := 8
const RATE := 24000

var samples: Array[float] = []
var last_beat := -1
var output_latency := 0.0

func begin(gain: float) -> void:
	samples.clear()
	last_beat = -1
	if not stream:
		stream = _make_click_track()
	volume_db = linear_to_db(gain)
	output_latency = AudioServer.get_output_latency()
	play()

func take_tap() -> bool:
	if not playing or samples.size() >= TOTAL:
		return false
	var heard := get_playback_position() + AudioServer.get_time_since_last_mix() - output_latency
	var nearest := roundi(heard / BEAT)
	if heard < 0.20 or nearest <= last_beat:
		return false
	last_beat = nearest
	samples.append((heard - nearest * BEAT) * 1000.0)
	if samples.size() == TOTAL:
		stop()
	return true

func measured_offset() -> int:
	if samples.is_empty():
		return 0
	var ordered := samples.duplicate()
	ordered.sort()
	var mid := floori(ordered.size() * 0.5)
	var value: float = ordered[mid]
	if ordered.size() % 2 == 0:
		value = (ordered[mid - 1] + ordered[mid]) * 0.5
	return clampi(roundi(value), -250, 250)

func _make_click_track() -> AudioStreamWAV:
	# Keep each click in a single rendered stream so frame rate cannot move the beat.
	# The track is comfortably longer than a normal calibration session.
	var frames := roundi(RATE * BEAT)
	var one_beat := PackedByteArray()
	one_beat.resize(frames * 2)
	for index in range(roundi(0.07 * RATE)):
		var t := float(index) / RATE
		var envelope := minf(t / 0.0015, 1.0) * exp(-76.0 * t)
		var sound := (sin(TAU * 1120 * t) * 0.65 + sin(TAU * 1550 * t) * 0.30) * envelope
		one_beat.encode_s16(index * 2, roundi(24575.0 * sound))
	var bytes := PackedByteArray()
	for i in range(128):
		bytes.append_array(one_beat)
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = RATE
	wav.data = bytes
	return wav
