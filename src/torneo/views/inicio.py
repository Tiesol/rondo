from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def inicio(request: HttpRequest) -> HttpResponse:
    return render(request, "torneo/inicio.html")
