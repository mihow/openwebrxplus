# OpenWebRX+ Development Guide

## Development Environment Setup

### Prerequisites

**System Requirements:**
- Linux (Debian/Ubuntu recommended)
- Python 3.5 or later
- Git
- Build tools (gcc, make, cmake)
- SDR hardware (optional for development)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/luarvique/openwebrxplus.git
cd openwebrxplus

# Install system dependencies (Debian/Ubuntu)
sudo apt-get update
sudo apt-get install -y \
    python3 python3-pip \
    libfftw3-dev \
    libsamplerate0-dev \
    libcodec2-dev \
    rtl-sdr \
    soapysdr-tools

# Install Python dependencies
pip3 install -r requirements.txt

# Build from source (optional, for development)
./buildall.sh
```

### Running Development Server

```bash
# Run directly
python3 openwebrx.py

# Or with module syntax
python3 -m owrx

# With custom config
python3 openwebrx.py --config /path/to/openwebrx.conf
```

**Access:** http://localhost:8073/

### Configuration for Development

**Minimal `openwebrx.conf`:**
```python
[config]
port = 8073
host = 0.0.0.0
data_directory = /tmp/openwebrx
temporary_directory = /tmp/openwebrx/tmp
log_level = DEBUG
```

**Web-based configuration:**
1. Start server
2. Navigate to http://localhost:8073/settings
3. Configure SDR devices and profiles

## Code Organization

### Adding New Features

#### 1. Adding a New SDR Driver

**Location:** `owrx/source/`

**Steps:**
1. Create new file `owrx/source/mynewsdr.py`
2. Inherit from `SdrSource`
3. Implement required methods
4. Register in `owrx/source/__init__.py`

**Example:**
```python
# owrx/source/mynewsdr.py
from owrx.source.connector import ConnectorSource

class MyNewSdrSource(ConnectorSource):
    def getDriver(self):
        return "mynewsdr"

    def getEventNames(self):
        return super().getEventNames() + ["custom_event"]

    def sendControlMessage(self, msg):
        # Send control to SDR hardware
        pass
```

**Register:**
```python
# owrx/source/__init__.py
from owrx.source.mynewsdr import MyNewSdrSource

# Add to source types
```

#### 2. Adding a New Demodulator

**Location:** `csdr/chain/`

**Steps:**
1. Create new chain class
2. Define input/output formats
3. Implement DSP pipeline
4. Register mode in `owrx/modes.py`

**Example:**
```python
# csdr/chain/mymode.py
from csdr.chain import Chain
from pycsdr.modules import *

class MyModeChain(Chain):
    def __init__(self, input_rate, output_rate):
        self.input_rate = input_rate
        self.output_rate = output_rate

        workers = [
            Shift(offset),
            FirDecimate(decimation),
            Bandpass(low_cut, high_cut),
            # ... your DSP chain
        ]

        super().__init__(workers)
```

**Register mode:**
```python
# owrx/modes.py
Modes.registerMode(DigitalMode(
    "mymode",
    name="My New Mode",
    modulation="usb",
    requirements=["mymode_decoder"],
    service=True,  # Background decoder
    bandpass=Bandpass(300, 3000)
))
```

#### 3. Adding a New Controller

**Location:** `owrx/controllers/`

**Steps:**
1. Create controller class
2. Inherit from appropriate base
3. Add route in `owrx/http.py`

**Example:**
```python
# owrx/controllers/mycontroller.py
from owrx.controllers.template import WebpageController

class MyController(WebpageController):
    def indexAction(self):
        self.serve_template("mypage.html", data={
            "title": "My Page"
        })
```

**Add route:**
```python
# owrx/http.py
from owrx.controllers.mycontroller import MyController

Router.add_route("/mypage", MyController)
```

#### 4. Adding a New JavaScript Module

**Location:** `htdocs/lib/`

**Steps:**
1. Create JS file
2. Implement module
3. Include in HTML templates

**Example:**
```javascript
// htdocs/lib/MyModule.js
function MyModule() {
    this.init = function() {
        console.log("MyModule initialized");
    };

    this.doSomething = function() {
        // Your code here
    };
}

MyModule.prototype.init.call(MyModule.prototype);
```

**Include:**
```html
<!-- htdocs/index.html -->
<script src="static/lib/MyModule.js"></script>
```

## Testing

### Running Tests

```bash
# Run all tests
python3 -m pytest test/

# Run specific test file
python3 -m pytest test/property/test_property_manager.py

# Run with coverage
python3 -m pytest --cov=owrx test/

# Run with verbose output
python3 -m pytest -v test/
```

### Writing Tests

**Location:** `test/`

**Example:**
```python
# test/property/test_my_feature.py
import unittest
from owrx.property import Property

class MyFeatureTest(unittest.TestCase):
    def test_property_creation(self):
        prop = Property(42)
        self.assertEqual(prop.getValue(), 42)

    def test_property_change(self):
        prop = Property(0)
        changed = False

        def on_change(value):
            nonlocal changed
            changed = True

        prop.wire(on_change)
        prop.setValue(100)
        self.assertTrue(changed)
```

### Test-Driven Development (TDD)

**Recommended Approach:**
1. Write test first (it should fail)
2. Implement minimal code to pass test
3. Refactor
4. Repeat

**Example TDD Flow:**
```bash
# 1. Write failing test
vim test/test_new_feature.py
python3 -m pytest test/test_new_feature.py  # FAILS

# 2. Implement feature
vim owrx/new_feature.py
python3 -m pytest test/test_new_feature.py  # PASSES

# 3. Refactor if needed
vim owrx/new_feature.py
python3 -m pytest test/test_new_feature.py  # Still PASSES
```

## Code Style

### Python Style Guide

**Follow PEP 8** (with some relaxations):
- Line length: 120 characters (not strict 80)
- Use 4 spaces for indentation
- Use snake_case for functions and variables
- Use PascalCase for classes

**Formatting Tools:**
```bash
# Format code
black owrx/ csdr/ test/

# Check style
flake8 owrx/ csdr/ test/ --max-line-length=120

# Type checking (optional)
mypy owrx/
```

**Pre-commit Hook:**
```bash
# .git/hooks/pre-commit
#!/bin/bash
black --check owrx/ csdr/ test/
if [ $? -ne 0 ]; then
    echo "Code not formatted. Run: black owrx/ csdr/ test/"
    exit 1
fi
```

### JavaScript Style Guide

**Style:**
- Use 4 spaces for indentation
- Use camelCase for variables and functions
- Use PascalCase for constructors
- Semicolons optional but consistent

**Linting:**
```bash
# Install ESLint
npm install -g eslint

# Check JavaScript
eslint htdocs/lib/*.js
```

## Debugging

### Server-Side Debugging

**Enable Debug Logging:**
```python
# In openwebrx.conf or code
import logging
logging.basicConfig(level=logging.DEBUG)

# For specific modules
logging.getLogger("owrx.dsp").setLevel(logging.DEBUG)
logging.getLogger("owrx.websocket").setLevel(logging.DEBUG)
```

**Using Python Debugger:**
```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or with Python 3.7+
breakpoint()
```

**Remote Debugging (PyCharm/VS Code):**
```python
import pydevd_pycharm
pydevd_pycharm.settrace('localhost', port=12345, stdoutToServer=True, stderrToServer=True)
```

### Client-Side Debugging

**Browser DevTools:**
- Console: `F12` → Console
- Network: Monitor WebSocket frames
- Performance: Profile CPU/memory
- Sources: Set breakpoints in JS

**Console Debugging:**
```javascript
// Log all WebSocket messages
const originalOnMessage = ws.onmessage;
ws.onmessage = function(event) {
    console.log("WS received:", event.data);
    originalOnMessage.call(this, event);
};

// Log demodulator changes
Demodulator.prototype.setFrequency = function(freq) {
    console.log("Tuning to:", freq);
    // ... original code
};
```

### DSP Pipeline Debugging

**Visualize DSP Chain:**
```python
# In owrx/dsp.py
def __init__(self):
    self.chain = self.buildChain()
    logger.debug(f"DSP chain: {self.chain}")

# Check chain structure
print(chain.getInputFormat())  # Input format
print(chain.getOutputFormat())  # Output format
print(chain.workers)  # All workers in chain
```

**Monitor Audio Flow:**
```bash
# Check if audio is flowing
# Look for audio device activity
ps aux | grep csdr
ls -l /proc/$(pgrep csdr)/fd/  # File descriptors
```

## Common Development Tasks

### Task 1: Add Support for New Digital Mode

**Example: Adding FT4 support (hypothetical)**

1. **Check feature availability:**
```python
# owrx/feature.py
class Ft4Decoder(Feature):
    def is_available(self):
        return shutil.which("ft4_decoder") is not None
```

2. **Create decoder chain:**
```python
# csdr/chain/ft4.py
class Ft4Chain(Chain):
    def __init__(self):
        workers = [
            AudioBandpass(300, 3000),
            Convert_f32_s16(),
            # ... FT4-specific processing
        ]
        super().__init__(workers)
```

3. **Register mode:**
```python
# owrx/modes.py
Modes.registerMode(DigitalMode(
    "ft4",
    name="FT4",
    modulation="usb",
    requirements=["ft4_decoder"],
    service=True
))
```

4. **Add decoder service:**
```python
# owrx/ft4.py
class Ft4Service(DecoderService):
    def run(self):
        # Start ft4_decoder process
        # Parse output
        # Send to clients
        pass
```

5. **Update UI:**
```javascript
// htdocs/lib/Modes.js
modes["ft4"] = {
    name: "FT4",
    bandwidth: 3000,
    defaultFrequency: 7047500
};
```

### Task 2: Add New SDR Hardware Support

**Example: Adding "MySDR" support**

1. **Create source driver:**
```python
# owrx/source/mysdr.py
class MySDRSource(ConnectorSource):
    def getDriver(self):
        return "mysdr"

    def getCommandMapper(self):
        return super().getCommandMapper().setMappings({
            "frequency": Option("--freq"),
            "sample_rate": Option("--rate"),
            "rf_gain": Option("--gain"),
        })
```

2. **Register source:**
```python
# owrx/source/__init__.py
from owrx.source.mysdr import MySDRSource
```

3. **Add form fields:**
```python
# owrx/form/sdr.py
class MySDRDeviceSection(SoapyConnectorDeviceSection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.append(Field("device", TextInput(), "Device string"))
        self.append(Field("rf_gain", IntInput(), "RF Gain"))
```

4. **Test:**
```bash
# Start OpenWebRX
python3 openwebrx.py

# Configure SDR in web UI
# Settings → SDR devices → Add device → Select "MySDR"
```

### Task 3: Add New Bookmark Category

**Example: Adding NOAA Weather Radio bookmarks**

1. **Create bookmark file:**
```json
// bookmarks.d/noaa_weather.json
{
    "name": "NOAA Weather Radio",
    "bookmarks": [
        {
            "name": "WXJ40 New York",
            "frequency": 162550000,
            "modulation": "nfm"
        },
        {
            "name": "WXL92 Los Angeles",
            "frequency": 162400000,
            "modulation": "nfm"
        }
    ]
}
```

2. **Reload bookmarks:**
```python
# owrx/bookmarks.py automatically loads from bookmarks.d/
# Restart server to pick up new file
```

### Task 4: Customize Waterfall Colors

**Example: Add custom color scheme**

1. **Define color palette:**
```python
# owrx/color.py
class MyCustomTheme(ColorScheme):
    def get_color_scheme(self):
        return [
            (0, 0, 0),      # Black (weak signals)
            (0, 0, 100),    # Blue
            (0, 100, 100),  # Cyan
            (0, 100, 0),    # Green
            (100, 100, 0),  # Yellow
            (100, 0, 0),    # Red (strong signals)
        ]

ColorScheme.register("my_custom", MyCustomTheme())
```

2. **Select in UI:**
```
Settings → Appearance → Waterfall colors → "My Custom"
```

## Performance Optimization

### Profiling Python Code

**CPU Profiling:**
```bash
# Profile with cProfile
python3 -m cProfile -o profile.stats openwebrx.py

# Analyze results
python3 -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumtime'); p.print_stats(20)"
```

**Memory Profiling:**
```bash
# Install memory_profiler
pip3 install memory_profiler

# Profile specific function
@profile
def my_function():
    # ... code

python3 -m memory_profiler my_module.py
```

### Optimizing DSP Chains

**Tips:**
- Minimize sample rate conversions
- Use integer decimation where possible
- Avoid unnecessary format conversions
- Share FFT across clients
- Reduce waterfall frame rate

**Example Optimization:**
```python
# Before (slow)
chain = [
    Convert_f32_s16(),
    Resample(2400000, 48000),  # Expensive
    Convert_s16_f32(),
    Demodulator()
]

# After (fast)
chain = [
    FirDecimate(50),  # 2400000 / 50 = 48000
    Demodulator()
]
```

### Database Query Optimization

**Use bulk operations:**
```python
# Bad: N queries
for item in items:
    db.query(item)

# Good: 1 query
db.bulk_query(items)
```

**Use prefetch patterns:**
```python
# Prefetch related data
bookmarks = Bookmarks.load_all()
bookmarks.prefetch_categories()
```

## Git Workflow

### Branch Strategy

**Branches:**
- `master` - Stable releases
- `develop` - Development branch
- `feature/*` - Feature branches
- `bugfix/*` - Bug fixes

**Workflow:**
```bash
# Create feature branch
git checkout -b feature/my-new-feature

# Make changes
git add .
git commit -m "Add new feature"

# Push to remote
git push -u origin feature/my-new-feature

# Create pull request (on GitHub)
```

### Commit Messages

**Format:**
```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Code style (formatting)
- `refactor:` Code refactoring
- `test:` Tests
- `chore:` Build/maintenance

**Example:**
```
feat: Add support for FT4 decoder

Implement FT4 decoder chain and service. Adds support for FT4
digital mode decoding using wsjtx.

Closes #123
```

### Committing Often

**Best Practice: Commit frequently**

```bash
# After implementing small feature
git add owrx/myfeature.py
git commit -m "feat: Implement basic MyFeature class"

# After adding tests
git add test/test_myfeature.py
git commit -m "test: Add tests for MyFeature"

# After documentation
git add docs/myfeature.md
git commit -m "docs: Document MyFeature usage"
```

**Benefits:**
- Easy to revert specific changes
- Clear development history
- Easier code review
- Better git bisect

## Deployment

### Building Debian Package

```bash
# Build package
dpkg-buildpackage -b -us -uc

# Install package
sudo dpkg -i ../openwebrx-plus_*.deb
```

### Building Docker Image

```bash
# Build image
docker build -t openwebrxplus:latest .

# Run container
docker run -d -p 8073:8073 openwebrxplus:latest
```

### Systemd Service

```bash
# Enable service
sudo systemctl enable openwebrx

# Start service
sudo systemctl start openwebrx

# Check status
sudo systemctl status openwebrx

# View logs
sudo journalctl -u openwebrx -f
```

## Troubleshooting

### SDR Not Detected

```bash
# Check USB device
lsusb

# Check SoapySDR
SoapySDRUtil --find

# Check driver
rtl_test  # For RTL-SDR
hackrf_info  # For HackRF
```

### Audio Not Working

```bash
# Check DSP chain
ps aux | grep csdr

# Check WebSocket connection
# Browser DevTools → Network → WS

# Check audio decoder
# Browser Console → Check for errors
```

### High CPU Usage

```bash
# Check process CPU
top -p $(pgrep -f openwebrx)

# Profile code
python3 -m cProfile -o profile.stats openwebrx.py

# Reduce FFT rate
# Settings → FFT FPS → Lower value
```

### Memory Leak

```bash
# Monitor memory
watch -n 1 'ps -p $(pgrep -f openwebrx) -o rss='

# Profile memory
python3 -m memory_profiler openwebrx.py
```

## Resources

**Official Documentation:**
- Draft docs: https://fms.komkon.org/OWRX/
- Original wiki: https://github.com/jketterl/openwebrx/wiki

**Community:**
- Telegram channel: https://t.me/openwebrx
- Telegram chat: https://t.me/openwebrx_chat

**Package Repository:**
- PPA: https://luarvique.github.io/ppa/

**Related Projects:**
- csdr: https://github.com/jketterl/csdr
- pycsdr: https://github.com/jketterl/pycsdr
- owrx-connector: https://github.com/jketterl/owrx-connector
- digiham: https://github.com/jketterl/digiham
