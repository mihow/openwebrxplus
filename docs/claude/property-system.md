# OpenWebRX+ Property System

## Overview

The property system is a reactive data management framework inspired by functional reactive programming (FRP). It provides observable values, change propagation, validation, filtering, and layering capabilities.

**Location:** `owrx/property/`

## Core Concepts

### 1. Property

A `Property` is an observable value that notifies subscribers when changed.

```python
from owrx.property import Property

prop = Property("initial value")

def on_change(new_value):
    print(f"Value changed to: {new_value}")

prop.wire(on_change)  # Subscribe to changes
prop.setValue("new value")  # Triggers on_change callback
```

**Key Methods:**
- `setValue(value)` - Set new value
- `getValue()` - Get current value
- `wire(callback)` - Subscribe to changes
- `unwire(callback)` - Unsubscribe

### 2. PropertyManager

A collection of properties accessible like a dictionary.

```python
from owrx.property import PropertyManager

props = PropertyManager()
props["frequency"] = 7074000
props["mode"] = "usb"

print(props["frequency"])  # 7074000
```

**Key Features:**
- Dictionary-like access (`props[key]`)
- Property iteration
- Bulk updates
- Change notifications

### 3. PropertyStack

Layered properties where values can be overridden at different levels.

```python
from owrx.property import PropertyStack, PropertyLayer

# Base layer
base = PropertyLayer()
base["frequency"] = 7074000
base["mode"] = "usb"

# Override layer
override = PropertyLayer()
override["mode"] = "lsb"  # Override only mode

stack = PropertyStack()
stack.addLayer(0, base)
stack.addLayer(1, override)  # Higher priority

print(stack["frequency"])  # 7074000 (from base)
print(stack["mode"])  # "lsb" (overridden)
```

**Layer Priority:**
- Higher layer numbers = higher priority
- If value not in high layer, falls through to lower layers
- Delete from top layer to reveal underlying value

**Use Cases:**
- Default config → User config → Profile config → Session overrides
- SDR settings with profile-specific overrides

### 4. PropertyLayer

A property overlay that can be added to a stack.

```python
layer = PropertyLayer()
layer["key"] = "value"
layer.replaceLayer({"new_key": "new_value"})  # Bulk replace
```

**Key Methods:**
- `replaceLayer(dict)` - Replace all properties at once
- Property access like PropertyManager

### 5. PropertyCarousel

A rotating collection of property sets (used for multi-profile SDR configs).

```python
from owrx.property import PropertyCarousel

carousel = PropertyCarousel()
carousel.addLayer(0, profile1_props)
carousel.addLayer(1, profile2_props)
carousel.addLayer(2, profile3_props)

carousel.switch()  # Rotate to next profile
```

**Use Cases:**
- SDR profiles (different frequencies/modes for same hardware)
- Scheduled receiver configurations

## Advanced Features

### Property Wiring

Connect properties so changes propagate automatically.

```python
source = Property(100)
target = Property(0)

def sync(value):
    target.setValue(value * 2)

source.wire(sync)
source.setValue(50)  # target becomes 100
```

### Property Filters

Transform property values through a pipeline.

```python
from owrx.property.filter import PropertyFilterChain, Filter

class MultiplyFilter(Filter):
    def __init__(self, factor):
        self.factor = factor

    def apply(self, value):
        return value * self.factor

source = Property(10)
filtered = PropertyFilterChain(source)
filtered.addFilter(MultiplyFilter(2))
filtered.addFilter(MultiplyFilter(3))

print(filtered.getValue())  # 60 (10 * 2 * 3)
source.setValue(5)
print(filtered.getValue())  # 30 (5 * 2 * 3)
```

**Built-in Filters:**
- `OrFilter` - Logical OR of multiple properties
- `AndFilter` - Logical AND of multiple properties
- Custom filters via `Filter` base class

### Property Validators

Validate values before assignment.

```python
from owrx.property.validators import IntValidator, RangeValidator

prop = Property(validator=IntValidator())
prop.setValue(42)  # OK
prop.setValue("not an int")  # Raises exception

freq_prop = Property(validator=RangeValidator(0, 30000000))
freq_prop.setValue(14074000)  # OK
freq_prop.setValue(-1000)  # Raises exception
```

**Built-in Validators:**
- `BoolValidator` - Boolean values
- `IntValidator` - Integer values
- `FloatValidator` - Float values
- `NumberValidator` - Int or float
- `StringValidator` - String values
- `RegexValidator` - Pattern matching
- `LambdaValidator` - Custom validation function

**Combining Validators:**
```python
from owrx.property.validators import AndValidator, OrValidator

# Must be int AND in range
validator = AndValidator(IntValidator(), RangeValidator(1, 100))

# Can be int OR float
validator = OrValidator(IntValidator(), FloatValidator())
```

### Property Deletion

Properties can be deleted to reveal underlying layer values.

```python
stack = PropertyStack()
base = PropertyLayer(foo="base_value")
override = PropertyLayer(foo="override_value")

stack.addLayer(0, base)
stack.addLayer(1, override)

print(stack["foo"])  # "override_value"
del stack["foo"]  # Delete from top layer
print(stack["foo"])  # "base_value" (revealed from base)
```

### Read-Only Properties

Wrap properties to prevent modification.

```python
from owrx.property import PropertyReadOnly

source = Property(42)
readonly = PropertyReadOnly(source)

print(readonly.getValue())  # 42
readonly.setValue(100)  # Raises exception
source.setValue(100)  # OK, readonly reflects change
print(readonly.getValue())  # 100
```

## Property System in OpenWebRX+

### Configuration Management

```
CoreConfig (defaults)
    ↓
PropertyStack
    ├─ Layer 0: Default config
    ├─ Layer 1: User config (from file)
    ├─ Layer 2: Profile config
    └─ Layer 3: Session overrides
```

**Example:**
```python
# Load default config
defaults = PropertyLayer()
defaults.update({
    "receiver_name": "OpenWebRX+",
    "receiver_location": "Unknown",
    "max_clients": 20
})

# Load user config
user_config = PropertyLayer()
user_config.update(load_from_file("/etc/openwebrx/settings.json"))

# Create stack
config = PropertyStack()
config.addLayer(0, defaults)
config.addLayer(1, user_config)

# User config overrides defaults
print(config["receiver_name"])  # User's custom name or default
```

### SDR Source Properties

Each SDR source has properties for its parameters:

```python
sdr = RtlSdrSource(props)
props["device"] = "rtl_tcp=127.0.0.1:1234"
props["sample_rate"] = 2400000
props["frequency"] = 14074000
props["rf_gain"] = 30
props["ppm"] = 0

# Changes to props automatically update SDR
props["frequency"] = 7074000  # SDR retunes
```

**Property Wiring in SDR:**
```python
def on_frequency_change(freq):
    sdr_hardware.set_frequency(freq)

props.wire("frequency", on_frequency_change)
```

### Profile Switching

SDR profiles use PropertyCarousel:

```python
carousel = PropertyCarousel()

profile1 = PropertyLayer(frequency=7074000, mode="usb")
profile2 = PropertyLayer(frequency=14074000, mode="usb")
profile3 = PropertyLayer(frequency=144800000, mode="fm")

carousel.addLayer(0, profile1)
carousel.addLayer(1, profile2)
carousel.addLayer(2, profile3)

# Switch between profiles
carousel.switch()  # Now on profile2
carousel.switch()  # Now on profile3
carousel.switch()  # Back to profile1
```

### Client-Specific Properties

Each client connection has its own property stack:

```python
client = OpenWebRxReceiverClient(conn)
client.stack = PropertyStack()
client.stack.addLayer(0, global_config)
client.stack.addLayer(1, client_overrides)

# Client can have different frequency than others
client.stack["frequency"] = 14074000
```

## Property Change Propagation

### Example: Frequency Change Flow

```
User changes frequency in UI
    ↓
WebSocket message: {type: "dspcontrol", params: {frequency: 7074000}}
    ↓
connection.py updates client property
    ↓
client.stack["frequency"] = 7074000
    ↓
Property change event fired
    ↓
DSP chain wired to frequency property
    ↓
dsp.py receives frequency change
    ↓
DSP chain reconfigured
    ↓
SDR source wired to DSP frequency property
    ↓
sdr.py receives frequency change
    ↓
SDR hardware retuned
    ↓
New audio flows to client
```

### Wiring Examples from Codebase

**Example 1: SDR Frequency Control**
```python
class SdrSource:
    def __init__(self, props):
        self.props = props
        self.props.wire("frequency", self._on_frequency_change)

    def _on_frequency_change(self, freq):
        self.connector.set_frequency(freq)
```

**Example 2: Client DSP Chain**
```python
class OpenWebRxReceiverClient:
    def __init__(self, conn):
        self.dsp = DspManager(self.stack)
        self.stack.wire("frequency", self.dsp.set_frequency)
        self.stack.wire("mode", self.dsp.set_mode)
```

**Example 3: Configuration Update**
```python
class Settings:
    def __init__(self):
        self.config = PropertyStack()
        self.config.wire("receiver_name", self._update_metadata)

    def _update_metadata(self, name):
        broadcast_to_all_clients({"receiverName": name})
```

## Testing the Property System

OpenWebRX+ has extensive tests for the property system:

**Test Files (in `/test/`):**
- `property/test_property_manager.py` - Basic property management
- `property/test_property_stack.py` - Stack behavior
- `property/test_property_layer.py` - Layer operations
- `property/test_property_carousel.py` - Carousel rotation
- `property/test_property_filter.py` - Filtering
- `property/test_validators.py` - Validation
- `property/test_property_readonly.py` - Read-only properties

**Run Tests:**
```bash
python3 -m pytest test/property/
```

## Common Patterns

### Pattern 1: Configuration with Defaults

```python
defaults = {
    "port": 8073,
    "host": "0.0.0.0",
    "max_clients": 20
}

config = PropertyStack()
config.addLayer(0, PropertyLayer(**defaults))

# Load user config if exists
if os.path.exists("config.json"):
    user_config = PropertyLayer()
    user_config.replaceLayer(json.load(open("config.json")))
    config.addLayer(1, user_config)
```

### Pattern 2: Temporary Override

```python
original_freq = props["frequency"]

# Temporarily override
override_layer = PropertyLayer(frequency=7074000)
stack.addLayer(99, override_layer)

# ... do something ...

# Restore
stack.removeLayer(99)
```

### Pattern 3: Property Mirroring

```python
source = Property(0)
mirror1 = Property(0)
mirror2 = Property(0)

def sync(value):
    mirror1.setValue(value)
    mirror2.setValue(value)

source.wire(sync)
```

### Pattern 4: Computed Properties

```python
frequency = Property(7074000)
wavelength = Property(0)

def compute_wavelength(freq):
    wavelength.setValue(299792458 / freq)  # c / f

frequency.wire(compute_wavelength)
frequency.setValue(14074000)  # wavelength auto-updates
```

## Performance Considerations

**Property System Overhead:**
- Change notification has minimal overhead
- Wiring callbacks are called synchronously
- Deep stacks (many layers) can slow lookups

**Best Practices:**
- Minimize number of layers in stacks
- Avoid excessive wiring (unnecessary callbacks)
- Use bulk updates (`replaceLayer`) when changing many properties
- Unwire callbacks when no longer needed

## Debugging Tips

**Enable Property Logging:**
```python
import logging
logging.getLogger("owrx.property").setLevel(logging.DEBUG)
```

**Trace Property Changes:**
```python
prop.wire(lambda v: print(f"Property changed to: {v}"))
```

**Inspect Stack Layers:**
```python
for priority, layer in stack.layers.items():
    print(f"Layer {priority}: {dict(layer)}")
```

## Property System Gotchas

1. **Deleting from stack deletes from top layer only**
   ```python
   del stack["key"]  # Only deletes from highest layer, may reveal lower value
   ```

2. **Wiring is persistent**
   ```python
   prop.wire(callback)
   # callback will be called forever unless unwired
   prop.unwire(callback)  # Don't forget to clean up!
   ```

3. **Validators run on setValue only**
   ```python
   prop = Property(validator=IntValidator())
   prop.setValue(42)  # Validation runs
   prop._value = "bypass"  # Direct assignment bypasses validation (don't do this!)
   ```

4. **Circular wiring causes infinite loops**
   ```python
   a = Property(0)
   b = Property(0)
   a.wire(lambda v: b.setValue(v))
   b.wire(lambda v: a.setValue(v))  # Infinite loop!
   ```

5. **Layer priority ties**
   ```python
   stack.addLayer(1, layer1)
   stack.addLayer(1, layer2)  # Same priority - undefined behavior
   ```
