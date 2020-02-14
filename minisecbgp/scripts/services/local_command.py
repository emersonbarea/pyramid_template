import subprocess


def local_command(command):
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    command_result, command_result_error = result.communicate()
    return result.poll(), command_result, command_result_error
