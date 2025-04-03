#Written by Leon Gold
import mmap
import tkinter as tk
import time
import csv
from datetime import datetime

analog = mmap.mmap(-1, 40, tagname='EECI_ADC12U12_OUT', access=mmap.ACCESS_READ)

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        
        self.master = master
        self.master.geometry("")
        self.master.title("ADC-12U12 Test")

        
        self.channel_max = [0] * 12
        self.channel_current = [0] * 12

        
        self.csv_filename = None
        self.csv_mode = None

        # For CSV updates
        self.start_time = time.time()

        # Pause state variable
        self.paused = False

        self.pack()
        self.create_widgets()

    def create_widgets(self):
        # Labels 
        self.labels_frame = tk.Frame(self)
        self.labels_frame.pack(pady=(0, 10))

        self.info_labels = []
        for i in range(12):
            label = tk.Label(self.labels_frame, text="", font=("Courier", 12))
            label.pack(anchor="w", pady=2)
            self.info_labels.append(label)

        # CSV Mode Buttons
        self.csv_button_frame = tk.Frame(self)
        self.csv_button_frame.pack(pady=(0, 10))

        self.overwrite_btn = tk.Button(
            self.csv_button_frame,
            text="Overwrite CSV",
            command=self.choose_overwrite_csv
        )
        self.overwrite_btn.grid(row=0, column=0, padx=5)

        self.append_btn = tk.Button(
            self.csv_button_frame,
            text="Append CSV",
            command=self.choose_append_csv
        )
        self.append_btn.grid(row=0, column=1, padx=5)

        self.new_btn = tk.Button(
            self.csv_button_frame,
            text="New CSV",
            command=self.choose_new_csv
        )
        self.new_btn.grid(row=0, column=2, padx=5)

        # Pause/Play button
        self.pause_button = tk.Button(self, text="Pause", command=self.toggle_pause)
        self.pause_button.pack(side="left", padx=20, pady=10)

        # Quit button
        self.quit_button = tk.Button(self, text="QUIT", fg="red", command=self.master.destroy)
        self.quit_button.pack(side="right", padx=20, pady=10)

  #CSV Functions
    def choose_overwrite_csv(self):
        #Overwrites the current CSV file 
        self.csv_filename = "channel_max_values.csv"
        self.csv_mode = "overwrite"
        self.init_csv("w", write_header=True)

    def choose_append_csv(self):
        #Appends data to the current CSV file without no header
        self.csv_filename = "channel_max_values.csv"
        self.csv_mode = "append"
        self.init_csv("a", write_header=False)

    def choose_new_csv(self):
        #Creates a new csv file named by what the current time is
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_filename = f"channel_max_values_{timestamp_str}.csv"
        self.csv_mode = "new"
        self.init_csv("w", write_header=True)

    def init_csv(self, mode, write_header):
        #Initializes the current csv and writes a header. Basic operation for first running program
        with open(self.csv_filename, mode, newline="") as file:
            writer = csv.writer(file)
            if write_header:
                writer.writerow(["Timestamp"] + [f"Channel {i+1} Max" for i in range(12)])

    def update_csv(self):
        #Appends the current csv based on the time and the reading
        if self.csv_filename and self.csv_mode:
            with open(self.csv_filename, "a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([datetime.now().isoformat()] + self.channel_max)

 
    def toggle_pause(self):
        #Changes the pause or play button to display text depending on whether paused or played.
        self.paused = not self.paused

        if self.paused:
            self.pause_button.config(text="Resume")
  
        else:
            self.pause_button.config(text="Pause")


    def update_labels(self):
       #Writing to the tkinter page.
        for i in range(12):
            self.info_labels[i]["text"] = (
                f"Input [{i+1:2}]: {self.channel_current[i]:>8}      Max Val: {self.channel_max[i]:>8}"
            )

    def getInputs(self):
        # Gets the input channel data
        if not self.paused:
            self.channel_current = [
                (analog[i] - 240) * 256 + analog[12 + i] for i in range(12)
            ]
            # Updates the maximum values 
            for i in range(12):
                self.channel_max[i] = max(self.channel_max[i], self.channel_current[i])
           
            self.update_labels()

            # Check if a second has passed to log to the csv
            if time.time() - self.start_time >= 1:
                self.update_csv()        
            
            #Resets max values.
            if time.time() - self.start_time >= 60:
                self.channel_max = [0] * 12 
                self.start_time = time.time()

        self.master.after(200, self.getInputs)


#Tkinter setup
root = tk.Tk()
app = Application(master=root)
app.getInputs()
app.mainloop()
