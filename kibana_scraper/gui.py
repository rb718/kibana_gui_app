
import logging
import threading
from datetime import datetime
import tkinter as tk
from tkinter.font import Font
import tkinter.scrolledtext as ScrolledText

from .main import scrape, export
from .signals import signals

logger = logging.getLogger(__name__)

WIDTH=400
HEIGHT=300
APP_TITLE="Kibana Scraper"

class TextHandler(logging.Handler):
    # This class allows you to log to a Tkinter Text or ScrolledText widget
    # Adapted from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06

    def __init__(self, text):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        # Store a reference to the Text it will log to
        self.text = text

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text.configure(state='normal')
            self.text.insert(tk.END, msg + '\n')
            self.text.configure(state='disabled')
            # Autoscroll to the bottom
            self.text.yview(tk.END)
        # This is necessary because we can't modify the Text from other threads
        self.text.after(0, append)


class RobotManager:
    robot = None

    def __init__(self, parent):
        self.parent = parent
        self.btn_text = None

    def toggle(self, *args, **kwargs):
        if self.robot is None:
            logger.info("Starting robot")
            self.start()
        else:
            logger.info("Stopping robot")
            self.stop()

    def set_btn_text(self, text):
        if self.parent is not None:
            self.parent.toggle_txt.set(text)

    def start(self):
        if self.robot is not None:
            logger.warn("Robot already running")
            return

        signals.stop = False
        scrape_args = (self.parent.username.get(), self.parent.password.get())
        self.robot = threading.Thread(target=scrape, args=scrape_args)
        self.robot.start()
        logger.info("Robot started")

    def stop(self):
        if self.robot is None:
            logger.warn("Robot is not in running state")
            return
        signals.stop = True

    def update(self):
        if self.robot is None:
            self.set_btn_text("Start Robot")
        else:
            if self.robot.is_alive():
                self.set_btn_text("Stop Robot")
            else:
                self.robot.join()
                logger.info("Robot stoped")
                self.robot = None

        self.parent.after(1000, self.update)



root = tk.Tk()

header_font = Font(family="Times New Roman", size=16)

class Application(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.winfo_toplevel().title(APP_TITLE)
        self.build_gui()

    def build_gui(self):
        self.top = TopFrame(self)
        self.top.pack(fill="x")
        self.center = CenterFrame(self)
        self.center.pack(fill="both", expand=True)
        
class TopFrame(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.configure(pady=5, padx=5)
        self.build_gui()

    def build_gui(self):
        self.label = tk.Label(self, text=APP_TITLE, font=header_font)
        self.label.pack(side="left")
        
class CenterFrame(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.configure(pady=5, padx=5)
        self.build_gui()

    def build_gui(self):
        self.log_viewer = LogViewer(self)
        self.log_viewer.pack(side="left", fill="both", expand=True)
        self.control_form = ControlForm(self, width=200)
        self.control_form.pack_propagate(0)
        self.control_form.pack(side="right", fill="y")

class LogViewer(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.configure(pady=5, padx=5)
        self.build_gui()
        self.text_handler = TextHandler(self.text)

        logger = logging.getLogger()
        logger.addHandler(self.text_handler)

    def build_gui(self):
        self.text = ScrolledText.ScrolledText(self, state='disabled')
        self.text.configure(font='TkFixedFont')
        self.text.pack(fill="both", expand=True)

class ControlForm(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.configure(pady=5, padx=5)
        self.robot_manager = RobotManager(self)
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.build_gui()
        self.robot_manager.update()

    def export(self, *args, **kwargs):
        intial_filename = datetime.now().strftime("%Y%m%d-%H%M%S.csv")
        file_path = tk.filedialog.asksaveasfilename(initialfile=intial_filename, defaultextension="csv")
        
        if file_path is not None and file_path != "" and file_path != ():
            try:
                logger.info("Exporting data to: %s", file_path)
                export(file_path)
                logger.info("Done!")
            except Exception as e:
                logger.info("Failed: %s", str(e))
        
        
    def quit(self, *args, **kwargs):
        self.winfo_toplevel().destroy()

    def build_gui(self):
        self.input_group = tk.Frame(self)
        self.input_group.pack(side="top", fill="x")

        self.username_label = tk.Label(self.input_group, text="Username", anchor="w")
        self.username_label.pack(fill="x", pady=2)

        self.username_entry = tk.Entry(self.input_group, textvariable=self.username)
        self.username_entry.pack(fill="x", pady=2)

        self.password_label = tk.Label(self.input_group, text="Password", anchor="w")
        self.password_label.pack(fill="x", pady=2)

        self.password_entry = tk.Entry(self.input_group, show="*", textvariable=self.password)
        self.password_entry.pack(fill="x", pady=2)

        self.btn_group = tk.Frame(self)
        self.btn_group.pack(side="bottom", fill="x")

        self.toggle_txt = tk.StringVar()
        self.toggle_txt.set("Start robot")

        self.toggle_btn = tk.Button(self.btn_group, textvariable=self.toggle_txt, command=self.robot_manager.toggle)
        self.toggle_btn.bind("<Return>", self.robot_manager.toggle)
        self.toggle_btn.pack(fill="x", pady=2)

        self.export_btn = tk.Button(self.btn_group, text="Export data", command=self.export)
        self.export_btn.bind("<Return>", self.export)
        self.export_btn.pack(fill="x", pady=2)

        self.quit_btn = tk.Button(self.btn_group, text="Quit", command=self.quit)
        self.quit_btn.bind("<Return>", self.quit)
        self.quit_btn.pack(fill="x", pady=2)

#canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT)
#canvas.place()

content = Application(root)
content.pack()

root.mainloop()


