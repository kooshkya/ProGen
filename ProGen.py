import os
import pty
import subprocess
import sys
import psutil
import time
import re
import signal
from colorama import Fore, Style, init
from multiprocessing import shared_memory

processes = {}
SCHED_EXT = 7

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

            print(f"PID: {pid}")
            print(f"Status: {status}")
            print(f"CPU Times: {cpu_times}")
            print(f"CPU Percent: {cpu_percent}%")
            print(f"Current CPU: {current_cpu}")
            print(f"CPU Affinity (CPUs it can run on): {cpu_affinity}")
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

def pause_resume(pid, action):
    if pid in processes:
        if action == 'pause':
            os.kill(pid, signal.SIGUSR1)
            print(f"Sent SIGUSR1 (pause) to process {pid}.")
        elif action == 'resume':
            os.kill(pid, signal.SIGUSR2)
            print(f"Sent SIGUSR2 (resume) to process {pid}.")
        else:
            print(f"{Fore.RED}Invalid action: {action}. Use 'pause' or 'resume'.")
    else:
        print(f"No process found with PID {pid}.")

init(autoreset=True)

def show_help():
    help_text = f"""
    {Fore.CYAN}Available Commands:
    {Fore.GREEN}- generate [timeout] [no-class]           {Fore.WHITE}: Spawn a process with an optional timeout (in seconds).
    {Fore.GREEN}- terminal <pid>                         {Fore.WHITE}: Open a terminal for the process with the given PID.
    {Fore.GREEN}- show <pid>                             {Fore.WHITE}: Show details of the process with the given PID.
    {Fore.GREEN}- change_class <pid>                     {Fore.WHITE}: Change scheduling policy of the process to SCX.
    {Fore.GREEN}- set_affinity <pid> <cpu list>          {Fore.WHITE}: Set the CPU affinity for the process with the given PID to the specified list of CPUs.
    {Fore.GREEN}- select_file <path>                     {Fore.WHITE}: Specify a file path to create shared memory with the process PID.
    {Fore.GREEN}- pause_resume <pid> <pause/resume>      {Fore.WHITE}: Pause or resume the process with the given PID.
    {Fore.GREEN}- list                                   {Fore.WHITE}: List all running processes.
    {Fore.GREEN}- kill <pid>                             {Fore.WHITE}: Kill the process with the given PID.
    {Fore.GREEN}- kill_all                               {Fore.WHITE}: Kill all spawned processes.
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

def main():
    generate_pattern = re.compile(r"^generate(?:\s+(\d+))?(?:\s+no-class)?$")
    terminal_pattern = re.compile(r"^terminal\s+(\d+)$")
    show_pattern = re.compile(r"^show\s+(\d+)$")
    change_sched_class_pattern = re.compile(r"^change_class\s+(\d+)$")
    select_file_pattern = re.compile(r"^select_file\s+(.*)$")
    kill_pattern = re.compile(r"^kill\s+(\d+)$")
    kill_all_pattern = re.compile(r"^kill_all$")
    pause_resume_pattern = re.compile(r"^pause_resume\s+(\d+)\s+(pause|resume)$")
    affinity_pattern = re.compile(r"^set_affinity\s+(\d+)\s+([\d,]+)$")

    print(f"{Fore.YELLOW}Welcome! Type '{Fore.GREEN}help{Fore.YELLOW}' to see available commands.")
    show_help()

    try:
        while True:
            user_input = input(f"{Fore.LIGHTBLUE_EX}Enter command: {Style.RESET_ALL}").strip()

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
                    action = match.group(2)
                    pause_resume(pid, action)
                except ValueError:
                    print(f"{Fore.RED}Invalid PID or action. Please enter a valid integer and action.")
                continue

            if user_input == "list":
                print(f"{Fore.CYAN}Listing all processes...")
                list_processes()
                continue

            if user_input == "exit":
                kill_all_processes()
                print(f"{Fore.MAGENTA}Exiting... Goodbye!")
                exit(0)

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
