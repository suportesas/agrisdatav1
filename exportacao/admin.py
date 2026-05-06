from django.contrib import admin
from .models import (
    SolicitacaoBooking,
    Booking,
    BookingContainer,
    BookingContainerHistory,
    OrdemColeta,
)


@admin.register(SolicitacaoBooking)
class SolicitacaoBookingAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cliente', 'status', 'data_solicitacao', 'empresa')
    list_filter = ('status', 'empresa')
    search_fields = ('nome', 'cliente__razao_social', 'codigo')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'solicitacao', 'status', 'transportadora', 'porto_origem', 'porto_destino', 'empresa')
    list_filter = ('status', 'tipo_exportacao', 'empresa')
    search_fields = ('codigo', 'solicitacao__nome')


@admin.register(BookingContainer)
class BookingContainerAdmin(admin.ModelAdmin):
    list_display = ('numero_container', 'booking', 'status', 'tipo_container', 'empresa')
    list_filter = ('status', 'tipo_container', 'empresa')
    search_fields = ('numero_container', 'booking__codigo')


@admin.register(BookingContainerHistory)
class BookingContainerHistoryAdmin(admin.ModelAdmin):
    list_display = ('container', 'status_from', 'status_to', 'data', 'empresa')
    list_filter = ('status_to', 'empresa')
    search_fields = ('container__numero_container', 'observacoes')


@admin.register(OrdemColeta)
class OrdemColetaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'booking', 'status', 'data_prevista', 'empresa')
    list_filter = ('status', 'empresa')
    search_fields = ('numero', 'booking__codigo', 'container__numero_container')
