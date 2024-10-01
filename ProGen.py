import os
import pty
import subprocess
import sys

processes = {}

def spawn_process():
    command = ['./a.out']
    
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

        if user_input == "generate":
            spawn_process()
        elif user_input.startswith("terminal "):
            _, pid_str = user_input.split()
            try:
                pid = int(pid_str)
                open_terminal(pid)
            except ValueError:
                print("Invalid PID.")
        elif user_input == "exit":
            exit(0)
        else:
            print("Unknown command. Use 'generate' to spawn a process or 'terminal <pid>' to open a terminal.")

if __name__ == "__main__":
    main()
