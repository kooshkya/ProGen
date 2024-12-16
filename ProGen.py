import os
import pty
import subprocess
import sys
import psutil
import time
import re
import signal
import threading
from colorama import Fore, Style, init
from multiprocessing import shared_memory

processes = {}
SCHED_EXT = 7

SCHEDULING_CLASSES = {
    0: "SCHED_OTHER",   # Default Linux time-sharing scheduler
    1: "SCHED_FIFO",    # First-In-First-Out real-time scheduler
    2: "SCHED_RR",      # Round-Robin real-time scheduler
    3: "SCHED_BATCH",   # Batch scheduler for CPU-intensive processes
    5: "SCHED_IDLE",    # Idle scheduler for very low priority tasks
    6: "SCHED_DEADLINE",# Deadline scheduler for real-time processes
    7: "SCHED_EXT",
}


class MinionProcess:
    def __init__(self, affinity, keep_cfs, scheduled_start_time, *run_stop_intervals):
        # This is relative to the start of the executor loop
        self.scheduled_start_time = scheduled_start_time
        
        # The minion program takes each run or stop interval as seconds nanoseconds so each entry in run_stop_intervals should be broken to these two parts
        self.run_stop_separated_intervals = []
        for x in run_stop_intervals:
            self.run_stop_separated_intervals.append(int(x))
            self.run_stop_separated_intervals.append(int((x - int(x)) * 10**9))
        self.run_stop_str_separated_intervals = [str(x) for x in self.run_stop_separated_intervals]

        self.pid = -1
        self.start_time = -1
        self.start_delay = 0
        self.end_time = -1
        self.end_status = None
        self.waiter_thread = None
        self.affinity = affinity
        self.keep_cfs = keep_cfs
        self.rusage = None

        # calculated stats
        self.turnaround_time = None
        self.cpu_time = None
        self.off_cpu_time = None

    def run(self):
        try:
            self.start_time = time.monotonic()
            pid = os.fork()
            if pid == 0:
                param = os.sched_param(0)
                if not self.keep_cfs:
                    os.sched_setscheduler(0, SCHED_EXT, param)
                if self.affinity:
                    os.sched_setaffinity(0, self.affinity)
                os.execl("./a.out", "./a.out", *self.run_stop_str_separated_intervals)
            else:
                self.pid = pid
                self.waiter_thread = threading.Thread(target=wait_on_child, args=(self,))
                self.waiter_thread.start()
        except OSError as e:
            print(f"Fork failed: {e}")

    def calculate_stats(self):
        self.turnaround_time = self.end_time - self.start_time
        self.cpu_time = self.rusage.ru_utime + self.rusage.ru_stime
        self.off_cpu_time = self.turnaround_time - self.cpu_time

    def __str__(self):
            scheduled_time_str = f"{Fore.CYAN}Scheduled Start Time:{Style.RESET_ALL} {self.scheduled_start_time:.6f} sec"
            run_stop_intervals_str = f"{Fore.GREEN}Run/Stop Intervals:{Style.RESET_ALL} " + ", ".join(self.run_stop_str_separated_intervals)
            pid_str = f"{Fore.YELLOW}PID:{Style.RESET_ALL} {self.pid}"
            start_delay_str = f"{Fore.YELLOW}Start Delay:{Style.RESET_ALL} {self.start_delay if self.start_delay else 'Not started yet'}"
            start_time_str = f"{Fore.YELLOW}Start Time:{Style.RESET_ALL} {self.start_time if self.start_time != -1 else 'Not started yet'}"
            end_time_str = f"{Fore.YELLOW}End Time:{Style.RESET_ALL} {self.end_time if self.end_time != -1 else 'Not finished yet'}"
            turnaround_time_str = f"{Fore.YELLOW}Turnaround Time:{Style.RESET_ALL} {self.turnaround_time if self.turnaround_time else 'Not finished yet'}"
            cpu_time_str = f"{Fore.YELLOW}CPU Time:{Style.RESET_ALL} {self.cpu_time if self.cpu_time else 'Not finished yet'}"
            off_cpu_time_str = f"{Fore.YELLOW}Off-CPU Time:{Style.RESET_ALL} {self.off_cpu_time if self.off_cpu_time else 'Not finished yet'}"
            end_status_str = f"{Fore.YELLOW}End Status:{Style.RESET_ALL} {self.end_status if self.end_status is not None else 'Not finished yet'}"
            
            return f"""{scheduled_time_str}
{run_stop_intervals_str}
{pid_str}
{start_delay_str}
{start_time_str}
{end_time_str}
{turnaround_time_str}
{cpu_time_str}
{off_cpu_time_str}
{end_status_str}
"""

def wait_on_child(minion: MinionProcess):
    pid, status, rusage = os.wait4(minion.pid, 0)
    now = time.monotonic()
    if pid == minion.pid:
        minion.end_status = status
        minion.end_time = now
        minion.rusage = rusage
        minion.calculate_stats()
        

def run_process_schedule(file_path):
    processes = parse_file(file_path)
    if not processes:
        return
    start = do_run_processes(proc_list=processes)
    for p in processes:
        p.start_delay = p.scheduled_start_time + start - p.start_time
        p.waiter_thread.join(timeout=None)
    end = time.monotonic()
    print(f"started at {start} ended at {end} total {end - start:.6f} seconds")
    for i, p in enumerate(processes):
        print(f"{i}:\n{str(p)}")
    print_stats(processes, start, end)


def print_stats(processes: list[MinionProcess], experiment_start, experiment_end):
    process_count = len(processes)
    off_cpu_times = sorted([x.off_cpu_time for x in processes])
    total_off_cpu_time = sum(off_cpu_times)
    total_cpu_time = sum(x.cpu_time for x in processes)
    avg_off_cpu_time = total_off_cpu_time / process_count
    experiment_duration = experiment_end - experiment_start
    throughput = process_count / experiment_duration
    avg_turnaround_time = sum(x.turnaround_time for x in processes) / process_count
    print(f"{Fore.GREEN}Experiment Duration:{Style.RESET_ALL}  {experiment_duration:.6f} s")
    print(f"{Fore.GREEN}Total CPU Time:{Style.RESET_ALL}  {total_cpu_time:.6f} s")
    print(f"{Fore.GREEN}Total Off-CPU Time:{Style.RESET_ALL}  {total_off_cpu_time:.6f} s")
    print(f"{Fore.GREEN}Average Off-CPU time:{Style.RESET_ALL}  {avg_off_cpu_time:.6f} s")
    print(f"{Fore.GREEN}Throughput:{Style.RESET_ALL}  {throughput:.6f} procs/s")
    print(f"{Fore.GREEN}Average Turnaround Time:{Style.RESET_ALL}  {avg_turnaround_time:.6f} s")


def parse_file(file_path):
    if not os.path.exists(file_path):
        print(f"{file_path} does not exists!")
        return None
    with open(file_path, "r") as f:
        lines = f.readlines()
        lines = [x.strip() for x in lines if x.strip()]
        lines = [x for x in lines if not x.startswith("#")]
        split_lines = [x.split() for x in lines]
        keep_cfs_indices = set()
        affinities = {}
        for i, line in enumerate(split_lines):
            if line[0] == "!":
                keep_cfs_indices.add(i)
                del line[0]
            if line[0].startswith("[") and line[0].endswith("]"):
                affinities[i] = set(int(x) for x in line[0][1:-1].split(","))
                del line[0]
        split_lines = [[float(y) for y in x] for x in split_lines]
        split_lines = sorted(split_lines, key = lambda x: x[0])
        processes = []
        for i, line in enumerate(split_lines):
            processes.append(MinionProcess(affinities.get(i, None), bool(i in keep_cfs_indices), *line))
        return processes


def do_run_processes(proc_list: list[MinionProcess]):
    start = time.monotonic()
    cursor = 0
    while(cursor < len(proc_list)):
        now = time.monotonic()
        if (now - start >= proc_list[cursor].scheduled_start_time):
            proc_list[cursor].run()
            cursor += 1
    return start

def process_details(pid):
    if pid in processes:
        try:
            proc = psutil.Process(pid)
            status = proc.status()
            cpu_times = proc.cpu_times()
            cpu_percent = proc.cpu_percent(interval=0.1)
            cpu_affinity = proc.cpu_affinity()
            current_cpu = proc.cpu_num()
            memory_info = proc.memory_info()
            policy = SCHEDULING_CLASSES.get(os.sched_getscheduler(pid), "Unknown")

            print(f"PID: {pid}")
            print(f"Status: {status}")
            print(f"CPU Times: {cpu_times}")
            print(f"CPU Percent: {cpu_percent}%")
            print(f"Current CPU: {current_cpu}")
            print(f"CPU Affinity (CPUs it can run on): {cpu_affinity}")
            print(f"Sched_Class: {policy}")
            print(f"Memory Info: {memory_info}")
            print(f"Elapsed Time Since Creation (seconds): {time.time() - proc.create_time()}")
        except psutil.NoSuchProcess:
            print(f"Process with PID {pid} does not exist.")
    else:
        print(f"No process found with PID {pid}.")

def list_processes():
    if processes:
        print("List of processes and their states:")
        for pid, (process, master_fd) in processes.items():
            try:
                proc = psutil.Process(pid)
                status = proc.status()
                print(f"PID: {pid}, Status: {status}")
            except psutil.NoSuchProcess:
                print(f"PID: {pid}, Status: dead")
    else:
        print("No processes spawned yet.")

def change_process_policy(pid):
    if pid in processes:
        try:
            param = os.sched_param(0)
            os.sched_setscheduler(pid, SCHED_EXT, param)
            print(f"Scheduler class set to SCHED_EXT for process {pid}")
        except OSError as e:
            print(f"Failed to set scheduler: {e}")
    else:
        print(f"No process found with PID {pid}.")


def set_affinity(pid, cpus):
    if pid in processes:
        try:
            proc = psutil.Process(pid)
            proc.cpu_affinity(cpus)
            print(f"Set CPU affinity for process {pid} to CPUs: {cpus}")
        except psutil.NoSuchProcess:
            print(f"Process with PID {pid} does not exist.")
    else:
        print(f"No process found with PID {pid}.")


def spawn_process(timeout: int=None, set_sched_class: bool=True):
    command = ['./a.out'] if not timeout else ['./a.out', str(timeout)]
    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(command, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd)
    pid = process.pid
    if set_sched_class:
        try:
            param = os.sched_param(0)
            os.sched_setscheduler(process.pid, SCHED_EXT, param)
            print(f"Scheduler class set to SCHED_EXT for process {process.pid}")
        except OSError as e:
            print(f"Failed to set scheduler: {e}")
    processes[pid] = (process, master_fd)
    print(f"Spawned process with PID {pid}.")
    return pid

def open_terminal(pid):
    if pid in processes:
        process, master_fd = processes[pid]
        print(f"Opening terminal for process {pid}. Type 'exit' to detach.")

        try:
            while True:
                output = os.read(master_fd, 1024).decode('utf-8')  
                while output:
                    sys.stdout.write(output)
                    sys.stdout.flush()
                    output = os.read(master_fd, 1024).decode('utf-8')  

                input_command = input()
                if input_command.lower() == 'exit':
                    break
                os.write(master_fd, (input_command + "\n").encode('utf-8'))

        except KeyboardInterrupt:
            print("\nExiting terminal.")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"No process found with PID {pid}.")

def create_shared_memory_with_file(file_path):
    pid = spawn_process(-1)

    if not os.path.isfile(file_path):
        print(f"{Fore.RED}Error: File {file_path} does not exist.{Style.RESET_ALL}")
        return
    
    shm = shared_memory.SharedMemory(create=True, size=os.path.getsize(file_path), name=f"shm_{pid}")

    with open(file_path, 'rb') as f:
        data = f.read()
        shm.buf[:len(data)] = data
    
    print(f"Created shared memory '{shm.name}' with size {shm.size} bytes and stored the contents of {file_path}.")
    return shm

def pause_resume(pid):
    if pid in processes:
        os.kill(pid, signal.SIGUSR1)
        print(f"Sent SIGUSR1 (pause/resume) to process {pid}.")
    else:
        print(f"No process found with PID {pid}.")

def step_exec(pid):
    if pid in processes:
        os.kill(pid, signal.SIGUSR1)
        print(f"Sent SIGUSR1 (pause/resume) to process {pid}.")
        time.sleep(1)
        os.kill(pid, signal.SIGUSR1)
        print(f"Sent SIGUSR1 (pause/resume) to process {pid}.")
    else:
        print(f"No process found with PID {pid}.")

def yield_process(pid):
    if pid in processes:
        os.kill(pid, signal.SIGUSR2)
        print(f"Sent SIGUSR2 (yield) to process {pid}.")
    else:
        print(f"No process found with PID {pid}.")

init(autoreset=True)

def show_help():
    help_text = f"""
    {Fore.CYAN}Available Commands:
    {Fore.GREEN}- run_sched [filename]                   {Fore.WHITE}: Run the schedule denoted in filename
    {Fore.GREEN}- generate [timeout] [no-class]          {Fore.WHITE}: Spawn a process with an optional timeout (in seconds).
    {Fore.GREEN}- terminal <pid>                         {Fore.WHITE}: Open a terminal for the process with the given PID.
    {Fore.GREEN}- show <pid>                             {Fore.WHITE}: Show details of the process with the given PID.
    {Fore.GREEN}- change_class <pid>                     {Fore.WHITE}: Change scheduling policy of the process to SCX.
    {Fore.GREEN}- set_affinity <pid> <cpu list>          {Fore.WHITE}: Set the CPU affinity for the process with the given PID to the specified list of CPUs.
    {Fore.GREEN}- select_file <path>                     {Fore.WHITE}: Specify a file path to create shared memory with the process PID.
    {Fore.GREEN}- pause_resume <pid>                     {Fore.WHITE}: Pause or resume the process with the given PID.
    {Fore.GREEN}- step_exec <pid>                        {Fore.WHITE}: Send two pause/resume signals with a 1 second distance to the give PID.
    {Fore.GREEN}- yield <pid>                            {Fore.WHITE}: Make a process yield.
    {Fore.GREEN}- list                                   {Fore.WHITE}: List all running processes.
    {Fore.GREEN}- kill <pid>                             {Fore.WHITE}: Kill the process with the given PID.
    {Fore.GREEN}- kill_all                               {Fore.WHITE}: Kill all spawned processes.
    {Fore.GREEN}- wait <pid>                             {Fore.WHITE}: Wait on process with pid
    {Fore.GREEN}- exit                                   {Fore.WHITE}: Exit the program.
    {Fore.GREEN}- help                                   {Fore.WHITE}: Show this help text.
    """
    print(help_text)

def kill_process(pid):
    if pid in processes:
        process, master_fd = processes[pid]
        process.terminate()
        del processes[pid]
        print(f"Killed process with PID {pid}.")
    else:
        print(f"No process found with PID {pid}.")

def kill_all_processes():
    for pid in list(processes.keys()):
        kill_process(pid)
    print("Killed all spawned processes.")

def wait_process(pid):
    pid, status = os.waitpid(pid, 0)
    print(f"Waited and got pid={pid}, status={status}")

def main():
    run_sched_pattern = re.compile(r"^(?:run_sched|rs)\s+([\w.]+)$")
    generate_pattern = re.compile(r"^generate(?:\s+(\d+))?(?:\s+no-class)?$")
    terminal_pattern = re.compile(r"^terminal\s+(\d+)$")
    show_pattern = re.compile(r"^show\s+(\d+)$")
    change_sched_class_pattern = re.compile(r"^change_class\s+(\d+)$")
    select_file_pattern = re.compile(r"^select_file\s+(.*)$")
    kill_pattern = re.compile(r"^kill\s+(\d+)$")
    kill_all_pattern = re.compile(r"^kill_all$")
    pause_resume_pattern = re.compile(r"^pause_resume\s+(\d+)$")
    step_exec_pattern = re.compile(r"^step_exec\s+(\d+)$")
    yield_pattern = re.compile(r"^yield\s+(\d+)$")
    affinity_pattern = re.compile(r"^set_affinity\s+(\d+)\s+([\d,]+)$")
    wait_process_pattern = re.compile(r"^wait\s+(\d+)$")

    print(f"{Fore.YELLOW}Welcome! Type '{Fore.GREEN}help{Fore.YELLOW}' to see available commands.")
    show_help()

    try:
        while True:
            user_input = input(f"{Fore.LIGHTBLUE_EX}Enter command: {Style.RESET_ALL}").strip()

            match = run_sched_pattern.match(user_input)
            if match:
                file_path = match.group(1)
                run_process_schedule(file_path)
                continue

            match = generate_pattern.match(user_input)
            if match:
                timeout = match.group(1)
                no_class = "no-class" in user_input
                if timeout:
                    print(f"{Fore.GREEN}Spawning a process with timeout {timeout} seconds...")
                    spawn_process(timeout=int(timeout), set_sched_class=not no_class)
                else:
                    print(f"{Fore.GREEN}Spawning a process with default timeout...")
                    spawn_process(set_sched_class=not no_class)
                continue

            match = affinity_pattern.match(user_input)
            if match:
                try:
                    pid = int(match.group(1))
                    cpus = list(map(int, match.group(2).split(',')))
                    print(f"{Fore.GREEN}Setting CPU affinity for PID {pid} to CPUs {cpus}...")
                    set_affinity(pid, cpus)
                except ValueError:
                    print(f"{Fore.RED}Invalid input. Please enter a valid PID and CPU list.")
                continue

            match = terminal_pattern.match(user_input)
            if match:
                try:
                    pid = int(match.group(1))
                    print(f"{Fore.GREEN}Opening terminal for PID {pid}...")
                    open_terminal(pid)
                except ValueError:
                    print(f"{Fore.RED}Invalid PID. Please enter a valid integer.")
                continue

            match = show_pattern.match(user_input)
            if match:
                try:
                    pid = int(match.group(1))
                    print(f"{Fore.GREEN}Showing details for PID {pid}...")
                    process_details(pid)
                except ValueError:
                    print(f"{Fore.RED}Invalid PID. Please enter a valid integer.")
                continue

            match = change_sched_class_pattern.match(user_input)
            if match:
                try:
                    pid = int(match.group(1))
                    change_process_policy(pid)
                except ValueError:
                    print(f"{Fore.RED}Invalid PID. Please enter a valid integer.")
                continue

            match = select_file_pattern.match(user_input)
            if match:
                file_path = match.group(1).strip()
                print(f"{Fore.GREEN}Creating shared memory from file: {file_path}...")
                create_shared_memory_with_file(file_path)
                continue

            match = kill_pattern.match(user_input)
            if match:
                try:
                    pid = int(match.group(1))
                    print(f"{Fore.GREEN}Killing process with PID {pid}...")
                    kill_process(pid)
                except ValueError:
                    print(f"{Fore.RED}Invalid PID. Please enter a valid integer.")
                continue

            match = kill_all_pattern.match(user_input)
            if match:
                print(f"{Fore.GREEN}Killing all spawned processes...")
                kill_all_processes()
                continue

            match = pause_resume_pattern.match(user_input)
            if match:
                try:
                    pid = int(match.group(1))
                    pause_resume(pid)
                except ValueError:
                    print(f"{Fore.RED}Invalid PID. Please enter a valid integer pid.")
                continue

            match = step_exec_pattern.match(user_input)
            if match:
                try:
                    pid = int(match.group(1))
                    step_exec(pid)
                except ValueError:
                    print(f"{Fore.RED}Invalid PID. Please enter a valid integer pid.")
                continue

            match = yield_pattern.match(user_input)
            if match:
                try:
                    pid = int(match.group(1))
                    yield_process(pid)
                except ValueError:
                    print(f"{Fore.RED}Invalid PID. Please enter a valid integer pid.")
                continue

            match = wait_process_pattern.match(user_input)
            if match:
                try:
                    pid = int(match.group(1))
                    wait_process(pid)
                except ValueError:
                    print(f"{Fore.RED}Invalid PID. Please enter a valid integer pid.")
                continue

            if user_input == "list" or user_input == "l":
                print(f"{Fore.CYAN}Listing all processes...")
                list_processes()
                continue

            if user_input == "exit":
                kill_all_processes()
                print(f"{Fore.MAGENTA}Exiting... Goodbye!")
                exit(0)

            if user_input == "clear":
                if os.name == 'nt':
                    os.system('cls')
                else:
                    os.system('clear')

            if user_input == "help":
                show_help()
                continue

            print(f"{Fore.RED}Unknown command. Type '{Fore.GREEN}help{Fore.RED}' for available commands.")

    except KeyboardInterrupt:
        print("\nExiting...")
        kill_all_processes()
        exit(0)

if __name__ == "__main__":
    main()
