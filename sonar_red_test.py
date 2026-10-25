import subprocess

from django.http import HttpResponse


def ping(request):
    host = request.GET.get("host")
    output = subprocess.check_output("ping -c 1 " + host, shell=True)
    return HttpResponse(output)
