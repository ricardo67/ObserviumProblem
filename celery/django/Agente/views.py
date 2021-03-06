from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required
from Observium.functions import (get_SNMP, walk_SNMP, listaWalk,
                                 listadeso, walk_SNMP_task)
from Administrador.models import Administrador
from Administrador.tasks import crearBDRRD
from .serializers import AgenteSerializer
from django.shortcuts import render, redirect
from .forms import FormAgente
from Administrador.constants import (lista_oid, monitoreosSNMP,
                                     rendimientoSNMP, serviciosSNMP)
from .models import Agente
import logging

logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)s] (%(threadName)-s) %(message)s')


def staff_required(login_url=None):
    return user_passes_test(lambda u: u.is_staff, login_url=login_url)


def sistemaop(lista):
    tiposistema = [[elemento[0], tipo]
                   for elemento in lista for tipo in listadeso
                   if tipo in elemento[1]]
    return tiposistema


def generartabla(listawalk):
    return [[agente[0], [[agente[2][j][i] for j in range(len(agente[2]))]
                         for i in range(int(agente[1]))]]
            for agente in listawalk]


@staff_required(login_url="/")
@login_required(login_url='/')
def VistaAgente(request):
    dias = []
    administrador = Administrador.objects.filter(
        Administrador_id=request.user.id)
    agentes = Agente.objects.filter(
        Administrador_Agente_id=request.user.id)
    respuesta = get_SNMP(agentes, lista_oid)
    for elemento in respuesta:
        if elemento[1][1] == 'error':
            dias.append([elemento[0], 'no se puede calcular'])
        else:
            trans = int(elemento[1][1])
            hor = (int(trans/3600))
            minu = int((trans-(hor*3600))/60)
            seg = trans-((hor*3600)+(minu*60))
            dias.append([elemento[0],
                         (str(hor)+"h "+str(minu)+"m "+str(seg)+"s")])
    lista = [[elemento[0], elemento[1][0]] for elemento in respuesta]
    sis = sistemaop(lista)
    listawalk = generartabla(walk_SNMP(agentes, listaWalk, 1))
    contexto = {'administradores': administrador,
                'agentes': agentes,
                'respuesta': respuesta,
                'lista': sis,
                'dias': dias,
                'listawalk': listawalk}
    return render(request,
                  'Agente/agente_vista.html',
                  contexto)


@staff_required(login_url="/")
@login_required(login_url='/')
def IndividualAgente(request, Id):
    administrador = Administrador.objects.filter(
        Administrador_id=request.user.id)
    agentes = Agente.objects.filter(
        Administrador_Agente_id=request.user.id)
    dias = []
    lista_discos = []
    agente = Agente.objects.get(id=Id)
    respuesta = get_SNMP([agente], lista_oid)
    lista = [[elemento[0], elemento[1][0]] for elemento in respuesta]
    sis = sistemaop(lista)
    for elemento in respuesta:
        if elemento[1][1] == 'error':
            dias.append([elemento[0], 'no se puede calcular'])
        else:
            trans = int(elemento[1][1])
            hor = (int(trans/3600))
            minu = int((trans-(hor*3600))/60)
            seg = trans-((hor*3600)+(minu*60))
            dias.append([elemento[0],
                         (str(hor)+"h "+str(minu)+"m "+str(seg)+"s")])
    imagenes = '/static/files/{}/{}/{}/img/'.format(
        agente.Comunidad, agente.Ip.replace(".", ""), agente.NombreHost)
    walk = walk_SNMP_task(agente, '1.3.6.1.4.1.2021.9.1.2')
    for elemento in walk:
        lista_discos.append('Disk{}'.format(elemento.value.replace("/", "_")))
    contexto = {'administradores': administrador,
                'agentes': agentes,
                'agente': agente,
                'respuesta': respuesta,
                'lista': sis,
                'dias': dias,
                'imagenes': imagenes,
                'monitoreosSNMP': monitoreosSNMP,
                'rendimientoSNMP': rendimientoSNMP,
                'serviciosSNMP': serviciosSNMP,
                'lista_discos': lista_discos}
    return render(request,
                  'Agente/agente_individual.html',
                  contexto)


@staff_required(login_url="/")
@login_required(login_url='/')
def AgregarAgente(request):
    administrador = Administrador.objects.filter(
        Administrador_id=request.user.id)
    agente = Agente.objects.filter(
        Administrador_Agente_id=request.user.id)
    if request.method == 'POST':
        form = FormAgente(request.POST)
        print(form)
        if form.is_valid():
            form.save()
        for elemento in agente:
            serializer = AgenteSerializer(elemento)
            crearBDRRD.delay(serializer.data)
        return redirect('VistaAgente')
    else:
        form = FormAgente()
        contexto = {'administradores': administrador,
                    'agentes': agente,
                    'form': form}
    return render(request,
                  'Agente/agente_agregar.html',
                  contexto)


@staff_required(login_url="/")
@login_required(login_url='/')
def EditarAgente(request, Id):
    administrador = Administrador.objects.filter(
        Administrador_id=request.user.id)
    agente = Agente.objects.get(id=Id)
    if request.method == 'GET':
        form = FormAgente(instance=agente)
    else:
        form = FormAgente(request.POST, request.FILES, instance=agente)
        if form.is_valid():
            form.save()
        return redirect('VistaAgente')
    return render(request,
                  'Agente/agente_form.html',
                  {'form': form,
                   'agente': agente,
                   'administradores': administrador})


@staff_required(login_url="/")
@login_required(login_url='/')
def EliminarAgente(request, Id):
    agente = Agente.objects.get(id=Id)
    administrador = Administrador.objects.filter(
        Administrador_id=request.user.id)
    if request.method == 'POST':
        agente.delete()
        return redirect('VistaAgente')
    return render(request,
                  'Agente/agente_borrar.html',
                  {'agente': agente,
                   'administradores': administrador})
