@echo off
cd /d %~dp0
call venv311\Scripts\activate
flet pack desktop_app.py --name "SchoolPlanner_v2.1.2" --add-data "advisor.py;." --add-data "excel_export.py;." --add-data "excel_import.py;." -- --hidden-import ortools --collect-all ortools
call deactivate
pause