# LoRa Support Installation Guide

This guide provides instructions for installing the lorarx decoder and enabling LoRa support in OpenWebRX+.

## What is lorarx?

**lorarx** is a LoRa decoder from the dxlAPRS toolchain by OE5DXL (Christian Rabler). It can decode:
- **LoRa APRS** - Position tracking and telemetry
- **LoRaWAN** - IoT sensor network frames
- **Meshtastic** - Off-grid messaging
- **FANET** - Paraglider/hang glider tracking

**License:** GPL-2.0+ (Open Source)
**Source:** https://github.com/oe5hpm/dxlAPRS

---

## Installation Methods

### Method 1: Pre-compiled Binary (Quickest)

**Supported architectures:**
- x86-64 (64-bit PC)
- x86-32 (32-bit PC)
- armv7hf (Raspberry Pi 2B and newer)

#### For x86_64 (Most Common)

```bash
# Download lorarx binary
wget http://oe5dxl.hamspirit.at:8025/aprs/bin/x86-64/lorarx

# Make executable
chmod +x lorarx

# Install to system path
sudo mv lorarx /usr/local/bin/

# Verify installation
lorarx -h
```

#### For Raspberry Pi (ARMv7)

```bash
# Download lorarx for ARM
wget http://oe5dxl.hamspirit.at:8025/aprs/bin/armv7hf/lorarx

# Make executable
chmod +x lorarx

# Install to system path
sudo mv lorarx /usr/local/bin/

# Verify installation
lorarx -h
```

#### For 32-bit x86

```bash
# Download lorarx for 32-bit
wget http://oe5dxl.hamspirit.at:8025/aprs/bin/x86-32/lorarx

# Make executable
chmod +x lorarx

# Install to system path
sudo mv lorarx /usr/local/bin/

# Verify installation
lorarx -h
```

---

### Method 2: Compile from Source (Recommended for Advanced Users)

If pre-compiled binaries don't work on your system, or you want the latest version:

```bash
# Install build dependencies
sudo apt update
sudo apt install build-essential git

# Clone dxlAPRS repository
cd /tmp
git clone https://github.com/oe5hpm/dxlAPRS.git
cd dxlAPRS/src

# Compile lorarx
make lorarx

# Check build output
ls -lh ../out-$(uname -m)/lorarx

# Install to system
sudo cp ../out-$(uname -m)/lorarx /usr/local/bin/
sudo chmod +x /usr/local/bin/lorarx

# Verify installation
lorarx -h
```

---

## Verify Installation in OpenWebRX+

Once lorarx is installed, verify it's detected by OpenWebRX+:

1. **Start OpenWebRX+:**
   ```bash
   python3 openwebrx.py
   ```

2. **Open Admin Panel:**
   - Navigate to `http://localhost:8073/settings`
   - Log in with admin credentials

3. **Check Features:**
   - Go to **Settings → Features**
   - Look for **"lora"** in the features list
   - Should show **✓ Available** with green checkmark

4. **Check Available Modes:**
   - The LoRa mode should appear in background services
   - Service name: **"LoRa"**

---

## Common Frequencies

Once installed, you can tune to common LoRa frequencies:

### Europe
- **LoRa APRS:** 433.775 MHz
- **LoRaWAN:** 868.1, 868.3, 868.5 MHz
- **Meshtastic:** 869.525 MHz
- **FANET:** 868.2 MHz

### United States
- **LoRa APRS:** 927.9 MHz (proposed)
- **LoRaWAN:** 902.3 - 927.5 MHz (8 channels)
- **Meshtastic:** 906.875 MHz

### Asia-Pacific
- **LoRa APRS:** 433 MHz
- **LoRaWAN:** 920-925 MHz (varies by country)

---

## Troubleshooting

### lorarx not found

If OpenWebRX+ can't find lorarx:

```bash
# Check if lorarx is in PATH
which lorarx

# If not found, verify installation location
ls -l /usr/local/bin/lorarx

# Make sure /usr/local/bin is in PATH
echo $PATH | grep /usr/local/bin

# If not in PATH, add it to ~/.bashrc or /etc/environment
export PATH="/usr/local/bin:$PATH"
```

### Binary won't execute

If you get "cannot execute binary file" error:

```bash
# Check architecture
uname -m

# Verify binary architecture
file /usr/local/bin/lorarx

# If mismatch, download correct binary or compile from source
```

### Permission denied

```bash
# Make sure lorarx is executable
sudo chmod +x /usr/local/bin/lorarx

# Verify permissions
ls -l /usr/local/bin/lorarx
```

### Feature not appearing in OpenWebRX+

1. Verify lorarx works standalone:
   ```bash
   lorarx -h
   ```

2. Restart OpenWebRX+:
   ```bash
   # Stop OpenWebRX+ (Ctrl+C)
   # Start again
   python3 openwebrx.py
   ```

3. Clear feature cache:
   ```bash
   # Remove cache
   rm -rf /var/lib/openwebrx/.cache/
   ```

---

## Advanced Configuration

### Custom lorarx Parameters

The default configuration decodes:
- **Bandwidth:** 125 kHz
- **Spreading Factors:** SF7, SF10, SF12
- **Sample Rate:** 250 kHz

To modify parameters, edit `csdr/module/toolbox.py`:

```python
class LoraRxModule(ExecModule):
    def __init__(self, sampleRate: int = 250000, jsonOutput: bool = True):
        cmd = [
            "lorarx", "-i", "/dev/stdin", "-f", "f32",
            "-b", "7",      # Bandwidth: 0-9 (7=125kHz)
            "-s", "12",     # SF12
            "-s", "11",     # SF11 (add more as needed)
            "-s", "10",     # SF10
            "-s", "9",      # SF9
            "-s", "8",      # SF8
            "-s", "7",      # SF7
            "-Q",           # Only output valid CRC frames
            "-w", "64",     # Downsample FIR length
            "-r", str(sampleRate),
        ]
        if jsonOutput:
            cmd += ["-j", "/dev/stdout"]
        super().__init__(Format.COMPLEX_FLOAT, Format.CHAR, cmd)
```

**Bandwidth values:**
- 0: 7.8 kHz
- 1: 10.4 kHz
- 2: 15.6 kHz
- 3: 20.8 kHz
- 4: 31.25 kHz
- 5: 41.7 kHz
- 6: 62.5 kHz
- 7: 125 kHz (default)
- 8: 250 kHz
- 9: 500 kHz

---

## References

- **lorarx Homepage:** http://oe5dxl.hamspirit.at:8025/aprs/
- **dxlAPRS Source:** https://github.com/oe5hpm/dxlAPRS
- **DXL Wiki (German):** https://dxlwiki.dl1nux.de/index.php?title=Lorarx
- **LoRa Alliance:** https://lora-alliance.org/
- **LoRa APRS:** https://lora-aprs.info/
- **Meshtastic:** https://meshtastic.org/

---

## Next Steps

After installation:
1. Configure your SDR for LoRa frequencies
2. Enable LoRa background service in OpenWebRX+
3. Monitor decoded frames in the web interface
4. Set up APRS reporting if using LoRa APRS

See the [Quick Start Guide](lora-quick-start-guide.md) for implementation details.
