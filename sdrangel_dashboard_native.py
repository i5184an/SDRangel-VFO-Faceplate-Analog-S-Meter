from datetime import datetime, timezone
import json
import math
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
import urllib.request
from PIL import Image, ImageTk


class SDRangelNativeModule:

  def __init__(self, root):
    self.root = root
    self.root.title("SDRangel - Shack Dashboard")
    self.root.configure(bg="#2b2b2b")  # Sfondo standard Qt Dark

    # Finestra sempre in primo piano (Chiodo)
    self.root.attributes("-topmost", True)
    self.is_pinned = True

    # Abilitazione ridimensionamento libero e soglia minima stile SDRangel
    self.root.resizable(True, True)
    self.root.minsize(280, 380)

    # Parametri S-Meter
    self.sens_val = 1.0
    self.offset_val = 0.0
    self.channel_val = 0
    self.current_s_value = 0.0
    self.filtered_signal_level = 0.0
    self.current_skin = "imageyellow.png"
    self.orig_pil_img = None
    self.canvas_width = 200
    self.canvas_height = 112

    # Parametri Frequenzimetro
    self.current_freq = 0.0
    self.available_channels = []
    self.target_channel_index = 0

    # Stato generale
    self.running = True
    self.data_lock = threading.Lock()
    self.api_connected = False

    # Caricamento dimensioni iniziali skin
    try:
      temp_img = Image.open(self.current_skin)
      orig_w, orig_h = temp_img.size
      self.canvas_width = int(orig_w * 0.4)
      self.canvas_height = int(orig_h * 0.4)
    except Exception:
      pass

    self.create_styles()
    self.create_widgets()

    # Thread di comunicazione REST API
    self.api_thread = threading.Thread(target=self.api_worker, daemon=True)
    self.api_thread.start()

    self.update_gui()
    self.update_clock()

  def create_styles(self):
    style = ttk.Style()
    style.theme_use("clam")
    # Stile Notebook a schede in stile Qt con linguette a sinistra (nw)
    style.configure(
        "TNotebook", background="#2b2b2b", borderwidth=0, tabposition="nw"
    )
    style.configure(
        "TNotebook.Tab",
        background="#3c3f41",
        foreground="#a9b7c6",
        font=("Segoe UI", 9, "bold"),
        padding=[12, 4],
        borderwidth=1,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", "#2b2b2b")],
        foreground=[("selected", "#519aba")],
    )

  def create_widgets(self):
    # Barra superiore stile titolo modulo SDRangel
    header_bar = tk.Frame(self.root, bg="#3c3f41", height=22)
    header_bar.pack(fill="x", padx=2, pady=2)
    tk.Label(
        header_bar,
        text=" 🎛️ SHACK DASHBOARD MODULE",
        font=("Segoe UI", 9, "bold"),
        fg="#ffffff",
        bg="#3c3f41",
    ).pack(side="left", padx=4)

    # Notebook (Linguette Controls e Setup)
    self.notebook = ttk.Notebook(self.root)
    self.notebook.pack(padx=4, pady=2, fill="both", expand=True)

    self.tab_main = tk.Frame(self.notebook, bg="#2b2b2b")
    self.tab_setup = tk.Frame(self.notebook, bg="#2b2b2b")

    self.notebook.add(self.tab_main, text=" Controls ")
    self.notebook.add(self.tab_setup, text=" Setup ")

    self.build_main_tab()
    self.build_setup_tab()

    # Barra di stato inferiore (Qt Status Bar style)
    status_bar = tk.Frame(self.root, bg="#323232", bd=1, relief="sunken")
    status_bar.pack(fill="x", padx=2, pady=2)

    self.status_lbl = tk.Label(
        status_bar,
        text="Initializing REST API...",
        font=("Segoe UI", 8),
        fg="#b0b0b0",
        bg="#323232",
    )
    self.status_lbl.pack(side="left", padx=4)

    self.live_lbl = tk.Label(
        status_bar,
        text="● OFFLINE",
        font=("Segoe UI", 8, "bold"),
        fg="#cc6666",
        bg="#323232",
    )
    self.live_lbl.pack(side="right", padx=4)

  def build_main_tab(self):
    # 1. S-METER PANEL (Stile QGroupBox Qt)
    smeter_group = tk.LabelFrame(
        self.tab_main,
        text=" Signal Meter ",
        font=("Segoe UI", 8, "bold"),
        fg="#a9b7c6",
        bg="#2b2b2b",
        bd=1,
        relief="groove",
    )
    smeter_group.pack(padx=6, pady=4, fill="x")

    smeter_header = tk.Frame(smeter_group, bg="#2b2b2b")
    smeter_header.pack(fill="x", padx=4, pady=2)
    tk.Label(
        smeter_header,
        text="Analog S-Meter",
        font=("Segoe UI", 8),
        fg="#808080",
        bg="#2b2b2b",
    ).pack(side="left")
    self.sig_label = tk.Label(
        smeter_header,
        text="S 0",
        font=("Segoe UI", 9, "bold"),
        fg="#519aba",
        bg="#2b2b2b",
    )
    self.sig_label.pack(side="right")

    canvas_container = tk.Frame(smeter_group, bg="#1e1e1e", bd=1, relief="sunken")
    canvas_container.pack(padx=4, pady=4)

    self.canvas = tk.Canvas(
        canvas_container,
        width=self.canvas_width,
        height=self.canvas_height,
        bg="#1e1e1e",
        highlightthickness=0,
    )
    self.canvas.pack()
    self.load_skin_image(self.current_skin)

    # 2. VFO / FREQUENCY PANEL
    freq_group = tk.LabelFrame(
        self.tab_main,
        text=" Active Demodulator VFO (Click to cycle) ",
        font=("Segoe UI", 8, "bold"),
        fg="#a9b7c6",
        bg="#2b2b2b",
        bd=1,
        relief="groove",
    )
    freq_group.pack(padx=6, pady=4, fill="x")

    freq_display_frame = tk.Frame(freq_group, bg="#1e1e1e", bd=1, relief="sunken")
    freq_display_frame.pack(padx=4, pady=4, fill="x")

    self.freq_label = tk.Label(
        freq_display_frame,
        text="00.000.000 Hz",
        font=("Consolas", 14, "bold"),
        fg="#6a8759",  # Verde tipico dei display digitali SDR
        bg="#1e1e1e",
        cursor="hand2",
    )
    self.freq_label.pack(padx=6, pady=6)
    self.freq_label.bind("<Button-1>", self.cycle_channel)

    # 3. UTC CLOCK PANEL
    clock_group = tk.LabelFrame(
        self.tab_main,
        text=" UTC Time Reference ",
        font=("Segoe UI", 8, "bold"),
        fg="#a9b7c6",
        bg="#2b2b2b",
        bd=1,
        relief="groove",
    )
    clock_group.pack(padx=6, pady=4, fill="x")

    clock_inner = tk.Frame(clock_group, bg="#2b2b2b")
    clock_inner.pack(padx=4, pady=4, fill="x")

    self.date_label = tk.Label(
        clock_inner,
        text="-------",
        font=("Segoe UI", 9),
        fg="#808080",
        bg="#2b2b2b",
    )
    self.date_label.pack(side="left")

    self.time_label = tk.Label(
        clock_inner,
        text="00:00:00",
        font=("Consolas", 12, "bold"),
        fg="#cc7832",  # Arancione scuro/ambra stile orologio radio
        bg="#2b2b2b",
    )
    self.time_label.pack(side="right")

  def build_setup_tab(self):
    setup_container = tk.Frame(self.tab_setup, bg="#2b2b2b")
    setup_container.pack(padx=8, pady=8, fill="both", expand=True)

    # Sezione Skin S-Meter
    tk.Label(
        setup_container,
        text="S-Meter Appearance",
        font=("Segoe UI", 8, "bold"),
        fg="#a9b7c6",
        bg="#2b2b2b",
    ).pack(anchor="w", pady=(0, 2))

    skin_frame = tk.Frame(setup_container, bg="#3c3f41", bd=1, relief="solid")
    skin_frame.pack(fill="x", pady=2)

    skins = [
        ("Yellow", "imageyellow.png"),
        ("White", "imagewhite.png"),
        ("Blue", "imageblue.png"),
        ("Black", "imageblack.png"),
        ("Green", "imagegreen.png"),
    ]
    self.skin_buttons = {}
    for name, filename in skins:
      btn = tk.Button(
          skin_frame,
          text=name,
          font=("Segoe UI", 8),
          bg="#3c3f41",
          fg="#ffffff",
          activebackground="#555555",
          activeforeground="#ffffff",
          command=lambda f=filename, n=name: self.change_skin(f, n),
          relief="flat",
          cursor="hand2",
      )
      btn.pack(side="left", expand=True, fill="x", padx=1, pady=2)
      self.skin_buttons[name] = btn

    # Sezione Parametri Calibration
    tk.Label(
        setup_container,
        text="Calibration Parameters",
        font=("Segoe UI", 8, "bold"),
        fg="#a9b7c6",
        bg="#2b2b2b",
    ).pack(anchor="w", pady=(8, 2))

    params_frame = tk.Frame(setup_container, bg="#3c3f41", padx=8, pady=6)
    params_frame.pack(fill="x", pady=2)

    r1 = tk.Frame(params_frame, bg="#3c3f41")
    r1.pack(fill="x", pady=2)
    tk.Label(
        r1,
        text="Sensitivity Multiplier:",
        font=("Segoe UI", 8),
        fg="#b0b0b0",
        bg="#3c3f41",
    ).pack(side="left")
    self.sens_entry = tk.Entry(
        r1,
        font=("Segoe UI", 8, "bold"),
        width=6,
        bg="#2b2b2b",
        fg="#ffffff",
        insertbackground="white",
        justify="center",
    )
    self.sens_entry.insert(0, str(self.sens_val))
    self.sens_entry.pack(side="right")

    r2 = tk.Frame(params_frame, bg="#3c3f41")
    r2.pack(fill="x", pady=2)
    tk.Label(
        r2,
        text="Offset dB Adjustment:",
        font=("Segoe UI", 8),
        fg="#b0b0b0",
        bg="#3c3f41",
    ).pack(side="left")
    self.offset_entry = tk.Entry(
        r2,
        font=("Segoe UI", 8, "bold"),
        width=6,
        bg="#2b2b2b",
        fg="#ffffff",
        insertbackground="white",
        justify="center",
    )
    self.offset_entry.insert(0, str(self.offset_val))
    self.offset_entry.pack(side="right")

    apply_btn = tk.Button(
        params_frame,
        text="Apply Configuration",
        font=("Segoe UI", 8, "bold"),
        bg="#365880",
        fg="white",
        activebackground="#4a76a8",
        command=self.apply_config,
        relief="flat",
        cursor="hand2",
    )
    apply_btn.pack(fill="x", pady=(6, 2))

    # Sezione Finestra (Pin)
    tk.Label(
        setup_container,
        text="Window Options",
        font=("Segoe UI", 8, "bold"),
        fg="#a9b7c6",
        bg="#2b2b2b",
    ).pack(anchor="w", pady=(8, 2))

    win_frame = tk.Frame(setup_container, bg="#3c3f41", padx=8, pady=6)
    win_frame.pack(fill="x", pady=2)

    self.pin_btn = tk.Button(
        win_frame,
        text="📌 Always on Top: ENABLED",
        font=("Segoe UI", 8),
        bg="#3c3f41",
        fg="#6a8759",
        activebackground="#555555",
        command=self.toggle_pin,
        relief="flat",
        cursor="hand2",
    )
    self.pin_btn.pack(fill="x")

  def toggle_pin(self):
    self.is_pinned = not self.is_pinned
    self.root.attributes("-topmost", self.is_pinned)
    if self.is_pinned:
      self.pin_btn.config(text="📌 Always on Top: ENABLED", fg="#6a8759")
    else:
      self.pin_btn.config(text="📌 Always on Top: DISABLED", fg="#808080")

  def load_skin_image(self, filename):
    try:
      self.orig_pil_img = Image.open(filename)
      orig_w, orig_h = self.orig_pil_img.size
      self.canvas_width = int(orig_w * 0.4)
      self.canvas_height = int(orig_h * 0.4)
      self.canvas.config(width=self.canvas_width, height=self.canvas_height)
      img = self.orig_pil_img.resize(
          (self.canvas_width, self.canvas_height), Image.Resampling.LANCZOS
      )
      self.bg_img = ImageTk.PhotoImage(img)
      self.canvas.delete("bg")
      self.canvas.create_image(0, 0, anchor="nw", image=self.bg_img, tags="bg")
      self.update_needle_graphics(self.current_s_value)
    except Exception as e:
      print(f"Cannot load image {filename}: {e}")

  def change_skin(self, filename, name):
    self.current_skin = filename
    self.load_skin_image(filename)
    for k, b in self.skin_buttons.items():
      if k == name:
        b.config(bg="#4c5052", fg="#519aba")
      else:
        b.config(bg="#3c3f41", fg="#ffffff")

  def apply_config(self):
    try:
      new_sens = float(self.sens_entry.get().strip())
    except ValueError:
      new_sens = 1.0
    try:
      new_off = float(self.offset_entry.get().strip())
    except ValueError:
      new_off = 0.0

    with self.data_lock:
      self.sens_val = new_sens
      self.offset_val = new_off
    self.status_lbl.config(text="Configuration updated successfully.")

  def update_needle_graphics(self, s_val):
    self.canvas.delete("needle")
    w = self.canvas_width
    h = self.canvas_height

    cx = 250 * (w / 500.0)
    cy = 265 * (h / 280.0)

    degrees = -58
    if s_val <= 9:
      degrees = -58 + (s_val * (58 / 9))
    else:
      overS9 = s_val - 9
      degrees = 0 + (overS9 * 7.5)
    degrees = max(-62, min(50, degrees))

    length = 210 * (h / 280.0)
    angle_rad = math.radians(degrees)

    tip_x = cx + length * math.sin(angle_rad)
    tip_y = cy - length * math.cos(angle_rad)

    self.canvas.create_line(
        cx, cy, tip_x, tip_y, fill="#b52b2b", width=2, tags="needle"
    )
    self.canvas.create_oval(
        cx - 6,
        cy - 6,
        cx + 6,
        cy + 6,
        fill="#2b2b2b",
        outline="#555555",
        width=2,
        tags="needle",
    )
    self.canvas.create_oval(
        cx - 2, cy - 2, cx + 2, cy + 2, fill="#cc6666", outline="", tags="needle"
    )

  def db_to_s_scale(self, db_val):
    if db_val <= -120.0:
      return 0.0
    s9_db = -29.0
    diff = db_val - s9_db
    if diff <= 0:
      s_val = 9.0 + (diff / 6.0)
      return max(0.0, s_val)
    else:
      s_val = 9.0 + (diff / 6.0)
      return min(19.0, s_val)

  def search_frequencies(self, obj, path=""):
    found = []
    if isinstance(obj, dict):
      for k, v in obj.items():
        curr_path = f"{path}.{k}" if path else k
        k_lower = k.lower()
        if (
            "freq" in k_lower or "center" in k_lower
        ) and isinstance(v, (int, float)):
          if v > 500000:
            found.append((curr_path, float(v)))
        found.extend(self.search_frequencies(v, curr_path))
    elif isinstance(obj, list):
      for idx, item in enumerate(obj):
        found.extend(self.search_frequencies(item, f"{path}[{idx}]"))
    return found

  def cycle_channel(self, event):
    with self.data_lock:
      if len(self.available_channels) > 1:
        self.target_channel_index = (self.target_channel_index + 1) % len(
            self.available_channels
        )
        self.status_lbl.config(
            text=f"Switched to channel index {self.target_channel_index}"
        )

  def api_worker(self):
    while self.running:
      channel_db = None
      detected_channels = []
      status_text = "Scanning REST API..."

      for dev_idx in range(3):
        url = f"http://127.0.0.1:8091/sdrangel/deviceset/{dev_idx}"
        try:
          req = urllib.request.Request(
              url,
              headers={
                  "User-Agent": "Mozilla/5.0",
                  "Accept": "application/json",
              },
          )
          with urllib.request.urlopen(req, timeout=0.25) as response:
            if response.status == 200:
              data = json.loads(response.read().decode())
              all_freqs = self.search_frequencies(data)

              center_freq = 0.0
              for path, val in all_freqs:
                if (
                    "center" in path.lower()
                    or "samplingdevice" in path.lower()
                ):
                  center_freq = val

              channels = data.get("channels", [])
              for idx, ch in enumerate(channels):
                title = ch.get("title", f"Ch {idx}")
                delta = ch.get("deltaFrequency", 0.0)

                ch_abs = 0.0
                ch_freqs = self.search_frequencies(ch)
                for p, fv in ch_freqs:
                  if "freq" in p.lower() and fv > 500000:
                    ch_abs = fv
                    break

                calc_freq = 0.0
                if ch_abs > 500000:
                  calc_freq = ch_abs
                elif center_freq > 500000:
                  calc = center_freq + delta
                  if calc > 500000:
                    calc_freq = calc

                if calc_freq > 500000:
                  power_db = -120.0
                  rep_url = f"http://127.0.0.1:8091/sdrangel/deviceset/{dev_idx}/channel/{idx}/report"
                  try:
                    req_rep = urllib.request.Request(
                        rep_url, headers={"User-Agent": "Mozilla/5.0"}
                    )
                    with urllib.request.urlopen(
                        req_rep, timeout=0.15
                    ) as resp_rep:
                      if resp_rep.status == 200:
                        rep_data = json.loads(resp_rep.read().decode())
                        for rk, rv in rep_data.items():
                          if isinstance(rv, dict):
                            for sub_k, sub_v in rv.items():
                              if "power" in sub_k.lower() and isinstance(
                                  sub_v, (int, float)
                              ):
                                power_db = float(sub_v)
                                break
                  except Exception:
                    pass

                  detected_channels.append({
                      "dev": dev_idx,
                      "chan": idx,
                      "freq": calc_freq,
                      "title": title,
                      "power": power_db,
                  })
        except Exception:
          continue

      with self.data_lock:
        self.available_channels = detected_channels
        if self.available_channels:
          if self.target_channel_index >= len(self.available_channels):
            self.target_channel_index = 0
          active = self.available_channels[self.target_channel_index]
          self.current_freq = active["freq"]
          channel_db = active["power"]
          self.api_connected = True
          status_text = (
              f"Dev {active['dev']} Ch {active['chan']} | {active['title']} |"
              f" {channel_db:.1f} dB"
          )
        else:
          self.api_connected = False
          self.current_freq = 0.0
          status_text = "No active demodulator found"

        if channel_db is not None:
          raw_s = self.db_to_s_scale(channel_db)
          self.filtered_signal_level = raw_s * self.sens_val

      if self.api_connected:
        self.root.after(
            0, lambda: self.live_lbl.config(text="● ONLINE", fg="#6a8759")
        )
        self.root.after(
            0, lambda: self.status_lbl.config(text=status_text, fg="#b0b0b0")
        )
      else:
        self.root.after(
            0, lambda: self.live_lbl.config(text="● NO DEMOD", fg="#cc7832")
        )
        self.root.after(
            0,
            lambda: self.status_lbl.config(
                text="Waiting for demodulator...", fg="#b0b0b0"
            ),
        )

      time.sleep(0.3)

  def update_gui(self):
    with self.data_lock:
      mapped_target = self.filtered_signal_level + self.offset_val
      mapped_target = max(0.0, min(19.0, mapped_target))
      f = self.current_freq

    diff = mapped_target - self.current_s_value
    self.current_s_value += diff * 0.2
    s_val = self.current_s_value
    self.update_needle_graphics(s_val)

    label = (
        f"S 9 +{round((s_val - 9) * 6)}dB"
        if s_val > 9
        else f"S {max(0, round(s_val))}"
    )
    self.sig_label.config(text=label)

    if f > 0:
      freq_str = f"{int(f):,}".replace(",", ".") + " Hz"
    else:
      freq_str = "---.---.--- Hz"
    self.freq_label.config(text=freq_str)

    self.root.after(40, self.update_gui)

  def update_clock(self):
    now_utc = datetime.now(timezone.utc)
    self.time_label.config(text=now_utc.strftime("%H:%M:%S"))
    self.date_label.config(text=now_utc.strftime("%Y-%m-%d UTC"))
    self.root.after(1000, self.update_clock)


if __name__ == "__main__":
  root = tk.Tk()
  app = SDRangelNativeModule(root)
  root.mainloop()