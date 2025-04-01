import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time

# Configure the serial port (update '/dev/ttyACM0' to your device if needed)
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

# Open a log file in append mode (data.txt in the same directory)
log_file = open("data.txt", "a")

# Data lists for each of the four channels
data1, data2, data3, data4 = [], [], [], []
# Buffer to accumulate tokens if lines are incomplete
token_buffer = []

def read_serial():
    """Reads one line from the serial port, logs it, and appends tokens to token_buffer."""
    try:
        line = ser.readline().decode('utf-8').strip()
    except Exception as e:
        print("Error reading from serial:", e)
        return
    if line:
        # Log the line to the file
        log_file.write(line + "\n")
        log_file.flush()  # Ensure immediate write
        # Split the line into tokens and add them to the buffer
        tokens = line.split()
        global token_buffer
        token_buffer.extend(tokens)

def process_tokens():
    """Processes tokens in groups of 4 and appends them to channel data lists."""
    global token_buffer
    while len(token_buffer) >= 4:
        sample_tokens = token_buffer[:4]
        del token_buffer[:4]
        try:
            values = [float(x) for x in sample_tokens]
            d1, d2, d3, d4 = values
            data1.append(d1)
            data2.append(d2)
            data3.append(d3)
            data4.append(d4)
            # Uncomment below for debugging:
            # print("Parsed sample:", values)
        except ValueError:
            print("Error converting tokens:", sample_tokens)

# Create figure and 4 subplots (one per channel)
fig, axs = plt.subplots(4, 1, sharex=True, figsize=(10, 8))
axs[0].set_ylabel("Quad phase")
axs[1].set_ylabel("In phase")
axs[2].set_ylabel("BioZ")
axs[3].set_ylabel("Adjusted BioZ")
axs[3].set_xlabel("Sample Index")
fig.suptitle("Real-Time Sensor Data (Sliding Window)")

def animate(frame):
    # Read a few lines from the serial port for faster processing
    for _ in range(5):
        read_serial()
    process_tokens()
    
    # Define sliding window size
    window = 100
    total_samples = len(data1)
    
    if total_samples > window:
        x_vals = list(range(total_samples - window, total_samples))
        p1 = data1[-window:]
        p2 = data2[-window:]
        p3 = data3[-window:]
        p4 = data4[-window:]
    else:
        x_vals = list(range(total_samples))
        p1, p2, p3, p4 = data1, data2, data3, data4

    # Clear and update each subplot with custom colors
    axs[0].cla()
    axs[0].plot(x_vals, p1, color='red', label="Channel 1")
    axs[0].set_ylabel("Quad phase")
    axs[0].legend(loc="upper left")
    
    axs[1].cla()
    axs[1].plot(x_vals, p2, color='green', label="Channel 2")
    axs[1].set_ylabel("In phase")
    axs[1].legend(loc="upper left")
    
    axs[2].cla()
    axs[2].plot(x_vals, p3, color='blue', label="Channel 3")
    axs[2].set_ylabel("BioZ")
    axs[2].legend(loc="upper left")
    
    axs[3].cla()
    axs[3].plot(x_vals, p4, color='purple', label="Channel 4")
    axs[3].set_ylabel("Adjusted BioZ")
    axs[3].set_xlabel("Sample Index")
    axs[3].legend(loc="upper left")
    
    # Redraw the figure title if needed
    fig.suptitle("Real-Time Sensor Data (Sliding Window)")

ani = animation.FuncAnimation(fig, animate, interval=50)
plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.show()
