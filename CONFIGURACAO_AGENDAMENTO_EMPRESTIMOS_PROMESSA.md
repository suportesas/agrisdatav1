# Configuracao de Agendamento - Promessas de Emprestimos

Este guia agenda a rotina automatica do comando:

py manage.py atualizar_emprestimos_promessa --quiet

## Arquivos criados

- scripts/atualizar_emprestimos_promessa_windows.ps1
- scripts/atualizar_emprestimos_promessa_linux.sh

## Windows (Task Scheduler)

Criar ou atualizar tarefa diaria as 07:00:

schtasks /Create /TN "ERP_Agricola_Emprestimos_Promessa" /SC DAILY /ST 07:00 /F /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\erp_agricola_novo\scripts\atualizar_emprestimos_promessa_windows.ps1"

Opcao recomendada para rodar a cada 4 horas (a partir das 07:00):

schtasks /Create /TN "ERP_Agricola_Emprestimos_Promessa" /SC HOURLY /MO 4 /ST 07:00 /F /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\erp_agricola_novo\scripts\atualizar_emprestimos_promessa_windows.ps1"

Para executar mesmo sem usuario logado (prompt elevado):

schtasks /Create /TN "ERP_Agricola_Emprestimos_Promessa" /SC HOURLY /MO 4 /ST 07:00 /F /RU "SYSTEM" /RL HIGHEST /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\erp_agricola_novo\scripts\atualizar_emprestimos_promessa_windows.ps1"

Executar manualmente para teste:

schtasks /Run /TN "ERP_Agricola_Emprestimos_Promessa"

Consultar status:

schtasks /Query /TN "ERP_Agricola_Emprestimos_Promessa" /V /FO LIST

## Linux (cron)

Dar permissao no script:

chmod +x /caminho/do/projeto/scripts/atualizar_emprestimos_promessa_linux.sh

Adicionar no crontab (todos os dias as 07:00):

0 7 * * * /caminho/do/projeto/scripts/atualizar_emprestimos_promessa_linux.sh

## Railway

Railway nao executa cron automaticamente no mesmo servico web. A recomendacao eh criar um segundo servico para job agendado.

Sugestao de rotina externa (GitHub Actions agendado):

- Agendar workflow com cron para executar:
  python manage.py atualizar_emprestimos_promessa --quiet
- Usar as mesmas variaveis de ambiente de producao

Alternativa: usar um provedor de cron HTTP para chamar endpoint interno protegido (se houver endpoint dedicado no futuro).

## Log de execucao

A saida de cada execucao eh gravada em:

logs/emprestimos_promessa_scheduler.log

## Validacao rapida

Comando manual para validar a rotina:

py manage.py atualizar_emprestimos_promessa
