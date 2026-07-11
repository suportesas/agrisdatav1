# Configuracao de Agendamento - Alertas ASO

Este guia agenda a rotina automatica do comando:

py manage.py notificar_alertas_aso --canal ambos

## Arquivos criados

- scripts/notificar_alertas_aso_windows.ps1
- scripts/notificar_alertas_aso_linux.sh

## Windows (Task Scheduler)

Criar ou atualizar tarefa diaria as 08:00:

schtasks /Create /TN "ERP_Agricola_Alertas_ASO" /SC DAILY /ST 08:00 /F /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"C:\erp_agricola_novo\scripts\notificar_alertas_aso_windows.ps1\""

Opcao recomendada para iniciar 07:00 e repetir a cada 4 horas:

schtasks /Create /TN "ERP_Agricola_Alertas_ASO" /SC HOURLY /MO 4 /ST 07:00 /F /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\erp_agricola_novo\scripts\notificar_alertas_aso_windows.ps1"

Para executar mesmo sem usuario logado (necessita prompt elevado/Administrador):

schtasks /Create /TN "ERP_Agricola_Alertas_ASO" /SC HOURLY /MO 4 /ST 07:00 /F /RU "SYSTEM" /RL HIGHEST /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\erp_agricola_novo\scripts\notificar_alertas_aso_windows.ps1"

Executar manualmente para teste:

schtasks /Run /TN "ERP_Agricola_Alertas_ASO"

Consultar status:

schtasks /Query /TN "ERP_Agricola_Alertas_ASO" /V /FO LIST

## Linux (cron)

Dar permissao no script:

chmod +x /caminho/do/projeto/scripts/notificar_alertas_aso_linux.sh

Adicionar no crontab (todos os dias as 08:00):

0 8 * * * /caminho/do/projeto/scripts/notificar_alertas_aso_linux.sh

## Log de execucao

A saida de cada execucao eh gravada em:

logs/alertas_aso_scheduler.log

## Observacoes

- Para enviar somente email: use --canal email
- Para enviar somente WhatsApp: use --canal whatsapp
- Para incluir vencidos: acrescente --incluir-vencidos
- Para simulacao sem envio: acrescente --dry-run
