import os
import pty
import subprocess
import sys
import psutil
import time

processes = {}


def process_details(pid):
    if pid in processes:
        try:
            proc = psutil.Process(pid)
            status = proc.status()
            cpu_times = proc.cpu_times()
            cpu_percent = proc.cpu_percent(interval=0.1)
            cpu_affinity = proc.cpu_affinity()
            memory_info = proc.memory_info()

            print(f"PID: {pid}")
            print(f"Status: {status}")
            print(f"CPU Times: {cpu_times}")
            print(f"CPU Percent: {cpu_percent}%")
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


def spawn_process(timeout: int=None):
    command = ['./a.out'] if not timeout else ['./a.out', str(timeout)]
    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(command, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd)
    
    pid = process.pid
    processes[pid] = (process, master_fd)
    print(f"Spawned process with PID {pid}.")


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



def main():
    while True:
        user_input = input("Enter command: ")

        if user_input.startswith("generate"):
            parts = user_input.split()
            if len(parts) > 1:
                try:
                    timeout = int(parts[1])
                    spawn_process(timeout=timeout)
                except ValueError:
                    print("Invalid timeout. Please provide a valid integer.")
            else:
                spawn_process()  
        elif user_input.startswith("terminal "):
            _, pid_str = user_input.split()
            try:
                pid = int(pid_str)
                open_terminal(pid)
            except ValueError:
                print("Invalid PID.")
        elif user_input.startswith("show "):
            _, pid_str = user_input.split()
            try:
                pid = int(pid_str)
                process_details(pid)
            except ValueError:
                print("Invalid PID.")
        elif user_input == "list":
            list_processes()
        elif user_input == "exit":
            exit(0)
        else:
            print("Unknown command. Use 'generate' to spawn a process or 'terminal <pid>' to open a terminal.")

if __name__ == "__main__":
    main()
