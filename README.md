# SDRangel VFO Faceplate & Analog S-Meter

A custom Python / PyQt5 desktop companion utility for **SDRangel**, built to give modern software-defined radio setups the classic look and feel of a vintage analog transceiver. It features an interactive rotary VFO tuning knob, a retro analog S-meter, step selection, and a full numeric keypad with positive/negative (`±`) offset support.

---

## 🌟 Key Features

* **Vintage Analog S-Meter**: Custom-rendered, high-readability retro meter reflecting real-time frequency scaling and visual feedback.
* **Interactive Rotary VFO Dial**: Smooth mouse-dragging and scroll-wheel tuning capability designed with realistic mechanical proportions.
* **Precision Numeric Keypad**: Allows direct frequency offset entry with a dedicated sign toggle (`±`) and `SET DEV` execution.
* **Dynamic Step Control**: Quick-selection buttons ranging from `1 Hz` to `10 kHz`.
* **Real-Time REST API Sync**: Bidirectional synchronization with SDRangel—tune via the utility or directly inside SDRangel's main GUI, and everything stays perfectly aligned.

---

## 🛠️ How It Works: Dynamic Channel Tuning & REST API Architecture

SDRangel features a powerful REST API that exposes device sets, hardware devices, and processing channels. Rather than relying on hardcoded endpoints, this application dynamically targets and controls active demodulators by resolving the hierarchical structure of the SDRangel server.

### 1. The SDRangel REST Hierarchy
The application communicates with SDRangel using a structured three-tier URL hierarchy:
* **Host & Port**: The base server address (e.g., `http://127.0.0.1:8091`).
* **Device Set (`devset`)**: Represents the active receiver chain or device group (e.g., `/sdrangel/deviceset/1`).
* **Channel (`chan_idx`)**: Represents the specific demodulator or modulator plugin instance inside that device set (e.g., `/channel/0`).

### 2. Dynamic Channel Types & Payload Structure
Different demodulators in SDRangel (such as `AMDemod`, `SSBDemod`, `FMDemod`, `NFMDemod`, etc.) require specific JSON keys for their configuration payloads. 

When you configure or auto-detect a channel, the application dynamically constructs payloads tailored to the active channel type. For example, updating the frequency offset for an AM demodulator sends a `PATCH` request structured as:

```json
{
  "channelType": "AMDemod",
  "direction": 0,
  "AMDemodSettings": {
    "inputFrequencyOffset": -500
  }
}
```
If you switch to an SSB demodulator (`SSBDemod`), the app automatically adapts the payload key to `"SSBDemodSettings"`, ensuring seamless compatibility across different modes without restarting the utility.

### 3. Auto-Detection Mechanism (`🔍 Auto-Detect Channel`)
To eliminate manual guesswork when setting up the app, the **Setup** tab includes an automated discovery routine:
1. The app sends an HTTP `GET` request to the device set endpoint: `http://<host>/sdrangel/deviceset/<devset_id>`.
2. It inspects the returned JSON response for the `channels` array.
3. It automatically reads the `channelType` of the first active channel (e.g., `AMDemod`) and populates the channel index and type fields, establishing an instant communication link.

### 4. Bidirectional Real-Time Synchronization
* **Outgoing Control (`PATCH`)**: Rotating the vintage dial, clicking step buttons, or entering an offset via the keypad (`SET DEV` with `±` support) immediately fires an asynchronous `PATCH` request to update the frequency offset in SDRangel.
* **Incoming Polling (`GET`)**: A background thread utilizing `QTimer` polls SDRangel's channel settings endpoint every second (`/sdrangel/deviceset/{devset}/channel/{chan_idx}/settings`). If you tune or modify settings directly inside the main SDRangel interface, the companion faceplate automatically detects the change and updates its display and S-meter in real time.

---

## 🚀 Installation & Requirements

1. **Prerequisites**: Make sure **Python** is installed on your PC (Python 3.x recommended).
2. Install the required dependencies via terminal:
   ```bash
   pip install PyQt5 requests
   ```
3. **Start SDRangel** with the Web REST server enabled (typically running on port `8091`).
4. **Run the script**:
   ```bash
   python sdrangel_vfo_app.py
   ```
5. **Configure via Setup Tab**:
   * Enter your SDRangel instance details (`http://127.0.0.1:8091`).
   * Specify your **Device Set ID** and **Channel Index**.
   * Click **🔍 Auto-Detect Channel** to automatically fetch the active demodulator parameters.
6. Switch back to the **Main** tab and enjoy precision tuning with a classic hardware feel!

---

## 🤖 Acknowledgments
* This project was entirely designed, developed, and refined with the assistance of **Gemini**.

## 📜 License
Distributed under the MIT License. Feel free to fork, modify, and improve for your own shack setup!<img width="1914" height="1077" alt="SDRAngel S-meter e vintage knob" src="https://github.com/user-attachments/assets/1a5c53e1-9a77-4984-9148-20d06441dc17" />
