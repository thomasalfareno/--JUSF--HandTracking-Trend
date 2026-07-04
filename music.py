import os
import time
import numpy as np
import pygame

class MusicPlayer:
    FILTER_NORMAL = 'NORMAL'
    FILTER_MUFFLED = 'MUFFLED'
    FILTER_LOFI = 'LOFI'

    def __init__(self):
        self.filepath = None
        self.is_loaded = False
        self._playing = False
        self._paused = False
        self.volume_map = []
        self.volume_map_bass = []
        self.volume_map_mid = []
        self.volume_map_treble = []
        self.chunk_duration_ms = 50
        self.normal_sound = None
        self.muffled_sound = None
        self.lofi_sound = None
        self.eq_bass_sound = None
        self.eq_mid_sound = None
        self.eq_treble_sound = None
        self.chan_normal = None
        self.chan_muffled = None
        self.chan_lofi = None
        self.chan_eq_bass = None
        self.chan_eq_mid = None
        self.chan_eq_treble = None
        self.filter_mode = self.FILTER_NORMAL
        self.current_normal_vol = 1.0
        self.current_muffled_vol = 0.0
        self.current_lofi_vol = 0.0
        self.hand_volume = 1.0
        self.eq_bass_gain = 1.0
        self.eq_mid_gain = 1.0
        self.eq_treble_gain = 1.0
        self._start_time = 0
        self._pause_offset = 0
        self._current_volume_level = 0.0
        self._current_bass_level = 0.0
        self._current_mid_level = 0.0
        self._current_treble_level = 0.0
        self._smooth_factor = 0.3
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except pygame.error:
            pygame.mixer.init()
        self.chan_normal = pygame.mixer.Channel(0)
        self.chan_muffled = pygame.mixer.Channel(1)
        self.chan_lofi = pygame.mixer.Channel(2)
        self.chan_eq_bass = pygame.mixer.Channel(3)
        self.chan_eq_mid = pygame.mixer.Channel(4)
        self.chan_eq_treble = pygame.mixer.Channel(5)

    def load(self, filepath):
        if not os.path.exists(filepath):
            print(f'[ERROR] File audio tidak ditemukan: {filepath}')
            return False
        self.filepath = filepath
        print(f'[INFO] Mendekode audio PCM & menganalisis volume...')
        try:
            s = pygame.mixer.Sound(filepath)
            self.normal_sound = s
            raw_bytes = s.get_raw()
            samples = np.frombuffer(raw_bytes, dtype=np.int16).reshape(-1, 2)
            mono_samples = samples.mean(axis=1)
            chunk_samples = int(44100 * (self.chunk_duration_ms / 1000.0))
            num_chunks = len(mono_samples) // chunk_samples
            reshaped = mono_samples[:num_chunks * chunk_samples].reshape(num_chunks, chunk_samples)
            rms_values = np.sqrt(np.mean(reshaped.astype(np.float32) ** 2, axis=1))
            max_rms = np.max(rms_values) if len(rms_values) > 0 else 1.0
            self.volume_map = (rms_values / max_rms).tolist()
            window = 24
            cumsum = np.cumsum(np.insert(samples, 0, 0, axis=0), axis=0)
            muffled_samples = (cumsum[window:] - cumsum[:-window]) / window
            padding = np.zeros((window - 1, 2), dtype=np.int16)
            muffled_samples = np.vstack([muffled_samples, padding]).astype(np.int16)
            self.muffled_sound = pygame.mixer.Sound(buffer=muffled_samples.tobytes())
            factor = 14
            lofi_samples = np.repeat(samples[::factor, :], factor, axis=0)[:len(samples)]
            if len(lofi_samples) < len(samples):
                pad_len = len(samples) - len(lofi_samples)
                lofi_samples = np.vstack([lofi_samples, np.zeros((pad_len, 2), dtype=np.int16)])
            self.lofi_sound = pygame.mixer.Sound(buffer=lofi_samples.tobytes())
            w_bass = 80
            w_treble = 8
            float_samples = samples.astype(np.float32)

            def lpf(arr, w):
                cumsum_eq = np.cumsum(np.insert(arr, 0, 0, axis=0), axis=0)
                ma = (cumsum_eq[w:] - cumsum_eq[:-w]) / w
                pad = np.zeros((w - 1, 2), dtype=np.float32)
                return np.vstack([ma, pad])
            bass_data = lpf(float_samples, w_bass)
            lpf_high = lpf(float_samples, w_treble)
            treble_data = float_samples - lpf_high
            mid_data = lpf_high - bass_data
            self.eq_bass_sound = pygame.mixer.Sound(buffer=bass_data.astype(np.int16).tobytes())
            self.eq_mid_sound = pygame.mixer.Sound(buffer=mid_data.astype(np.int16).tobytes())
            self.eq_treble_sound = pygame.mixer.Sound(buffer=treble_data.astype(np.int16).tobytes())

            def calculate_volume_map(data_samples):
                mono = data_samples.mean(axis=1)
                num_chunks_band = len(mono) // chunk_samples
                reshaped_band = mono[:num_chunks_band * chunk_samples].reshape(num_chunks_band, chunk_samples)
                rms = np.sqrt(np.mean(reshaped_band.astype(np.float32) ** 2, axis=1))
                return rms
            rms_bass = calculate_volume_map(bass_data)
            rms_mid = calculate_volume_map(mid_data)
            rms_treble = calculate_volume_map(treble_data)
            self.volume_map_bass = (rms_bass / max_rms).tolist()
            self.volume_map_mid = (rms_mid / max_rms).tolist()
            self.volume_map_treble = (rms_treble / max_rms).tolist()
        except Exception as e:
            print(f'[ERROR] Gagal memproses audio PCM: {e}')
            return False
        self.is_loaded = True
        print(f'[OK] Audio & DSP siap: {len(self.volume_map)} chunks.')
        return True

    def play(self):
        if not self.is_loaded:
            return
        if self._paused:
            self.chan_normal.unpause()
            self.chan_muffled.unpause()
            self.chan_lofi.unpause()
            self.chan_eq_bass.unpause()
            self.chan_eq_mid.unpause()
            self.chan_eq_treble.unpause()
            self._paused = False
            self._start_time = time.time() - self._pause_offset
        else:
            self.chan_normal.play(self.normal_sound, loops=-1)
            self.chan_muffled.play(self.muffled_sound, loops=-1)
            self.chan_lofi.play(self.lofi_sound, loops=-1)
            self.chan_eq_bass.play(self.eq_bass_sound, loops=-1)
            self.chan_eq_mid.play(self.eq_mid_sound, loops=-1)
            self.chan_eq_treble.play(self.eq_treble_sound, loops=-1)
            self._start_time = time.time()
            self._pause_offset = 0
        self._playing = True
        self._apply_channel_volumes()

    def pause(self):
        if self._playing and (not self._paused):
            self.chan_normal.pause()
            self.chan_muffled.pause()
            self.chan_lofi.pause()
            self.chan_eq_bass.pause()
            self.chan_eq_mid.pause()
            self.chan_eq_treble.pause()
            self._paused = True
            self._pause_offset = time.time() - self._start_time

    def toggle(self):
        if self._paused:
            self.play()
        elif self._playing:
            self.pause()
        else:
            self.play()

    def stop(self):
        self.chan_normal.stop()
        self.chan_muffled.stop()
        self.chan_lofi.stop()
        self.chan_eq_bass.stop()
        self.chan_eq_mid.stop()
        self.chan_eq_treble.stop()
        self._playing = False
        self._paused = False
        self._pause_offset = 0

    def is_playing(self):
        return self._playing and (not self._paused)

    def get_pos(self):
        if not self._playing:
            return 0.0
        if self._paused:
            return self._pause_offset
        elapsed = time.time() - self._start_time
        if self.normal_sound:
            length = self.normal_sound.get_length()
            if length > 0:
                return elapsed % length
        return elapsed

    def set_filter(self, mode):
        if mode in (self.FILTER_NORMAL, self.FILTER_MUFFLED, self.FILTER_LOFI):
            self.filter_mode = mode

    def set_hand_volume(self, height_ratio):
        self.hand_volume = max(0.0, min(1.0, height_ratio))

    def set_eq_gains(self, bass, mid, treble):
        self.eq_bass_gain = max(0.0, min(2.0, bass))
        self.eq_mid_gain = max(0.0, min(2.0, mid))
        self.eq_treble_gain = max(0.0, min(2.0, treble))
        self._apply_channel_volumes()

    def update_dsp(self, dt):
        target_normal = self.hand_volume if self.filter_mode == self.FILTER_NORMAL else 0.0
        target_muffled = self.hand_volume if self.filter_mode == self.FILTER_MUFFLED else 0.0
        target_lofi = self.hand_volume if self.filter_mode == self.FILTER_LOFI else 0.0
        fade_speed = dt * 6.0
        self.current_normal_vol += (target_normal - self.current_normal_vol) * fade_speed
        self.current_muffled_vol += (target_muffled - self.current_muffled_vol) * fade_speed
        self.current_lofi_vol += (target_lofi - self.current_lofi_vol) * fade_speed
        self._apply_channel_volumes()

    def _apply_channel_volumes(self):
        if self._playing:
            self.chan_normal.set_volume(0.0)
            self.chan_eq_bass.set_volume(self.current_normal_vol * self.eq_bass_gain)
            self.chan_eq_mid.set_volume(self.current_normal_vol * self.eq_mid_gain)
            self.chan_eq_treble.set_volume(self.current_normal_vol * self.eq_treble_gain)
            self.chan_muffled.set_volume(self.current_muffled_vol)
            self.chan_lofi.set_volume(self.current_lofi_vol)

    def get_volume_level(self):
        target = 0.0
        if self.is_playing() and self.volume_map:
            elapsed_ms = self.get_pos() * 1000
            chunk_index = int(elapsed_ms / self.chunk_duration_ms)
            chunk_index = chunk_index % len(self.volume_map)
            target = self.volume_map[chunk_index]
        multiplier = 1.0
        if self.filter_mode == self.FILTER_MUFFLED:
            multiplier = 0.8
        elif self.filter_mode == self.FILTER_LOFI:
            multiplier = 1.2
        target = target * self.hand_volume * multiplier
        self._current_volume_level += (target - self._current_volume_level) * self._smooth_factor
        return self._current_volume_level

    def get_band_volume_levels(self):
        bass_t = 0.0
        mid_t = 0.0
        treble_t = 0.0
        if self.is_playing():
            elapsed_ms = self.get_pos() * 1000
            chunk_index = int(elapsed_ms / self.chunk_duration_ms)
            if self.volume_map_bass:
                idx = chunk_index % len(self.volume_map_bass)
                bass_t = self.volume_map_bass[idx]
            if self.volume_map_mid:
                idx = chunk_index % len(self.volume_map_mid)
                mid_t = self.volume_map_mid[idx]
            if self.volume_map_treble:
                idx = chunk_index % len(self.volume_map_treble)
                treble_t = self.volume_map_treble[idx]
        if self.filter_mode == self.FILTER_MUFFLED:
            bass_t *= 1.2
            mid_t *= 0.2
            treble_t *= 0.05
        elif self.filter_mode == self.FILTER_LOFI:
            bass_t *= 0.8
            mid_t *= 1.2
            treble_t *= 1.2
        else:
            bass_t *= self.eq_bass_gain
            mid_t *= self.eq_mid_gain
            treble_t *= self.eq_treble_gain
        bass_t *= self.hand_volume
        mid_t *= self.hand_volume
        treble_t *= self.hand_volume
        self._current_bass_level += (bass_t - self._current_bass_level) * self._smooth_factor
        self._current_mid_level += (mid_t - self._current_mid_level) * self._smooth_factor
        self._current_treble_level += (treble_t - self._current_treble_level) * self._smooth_factor
        return (self._current_bass_level, self._current_mid_level, self._current_treble_level)

    def get_elapsed_str(self):
        elapsed = self.get_pos()
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        return f'{mins:02d}:{secs:02d}'

    def cleanup(self):
        self.stop()
        pygame.mixer.quit()
