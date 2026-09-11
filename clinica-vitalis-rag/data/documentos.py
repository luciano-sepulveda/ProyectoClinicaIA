"""
documentos.py
--------------
Documentos de ejemplo (simulados) que representan las fuentes internas
y externas de Clínica Vitalis. En un despliegue real, estos vendrían de
los manuales PDF/Word y de las guías MINSAL descargadas.

Cada documento incluye metadata: sede, tipo (interna/externa) y categoria,
tal como se especifica en el apartado de "Preprocesamiento" del informe.
"""

DOCUMENTOS = [
    {
        "id": "doc_001",
        "titulo": "Protocolo de Preparación - Examen de Sangre (Sede Providencia)",
        "sede": "Providencia",
        "tipo": "interna",
        "categoria": "examen",
        "texto": (
            "Para el examen de sangre general, el paciente debe asistir en "
            "ayuno de 8 horas. Se recomienda no consumir alcohol 24 horas "
            "antes. El examen se realiza de lunes a viernes entre 08:00 y "
            "11:00 hrs en el laboratorio de la sede Providencia."
        ),
    },
    {
        "id": "doc_002",
        "titulo": "Protocolo de Preparación - Examen de Sangre (Sede Las Condes)",
        "sede": "Las Condes",
        "tipo": "interna",
        "categoria": "examen",
        "texto": (
            "El examen de sangre general en la sede Las Condes requiere "
            "ayuno de 8 a 10 horas. Se atiende con orden de reserva previa "
            "entre 07:30 y 10:30 hrs."
        ),
    },
    {
        "id": "doc_003",
        "titulo": "Indicaciones Post-Consulta Dermatológica",
        "sede": "Todas",
        "tipo": "interna",
        "categoria": "post-consulta",
        "texto": (
            "Tras una consulta dermatológica con procedimiento tópico, evite "
            "exposición solar directa por 48 horas y no aplique cosméticos "
            "sobre la zona tratada durante 24 horas."
        ),
    },
    {
        "id": "doc_004",
        "titulo": "Cobertura Convenio Isapre Consalud",
        "sede": "Todas",
        "tipo": "interna",
        "categoria": "convenio",
        "texto": (
            "Consalud cubre el 70% del valor de consultas de especialidad y "
            "el 50% de exámenes de laboratorio en Clínica Vitalis, sujeto al "
            "plan contratado por el paciente."
        ),
    },
    {
        "id": "doc_005",
        "titulo": "Guía MINSAL - Recomendaciones Generales de Ayuno para Exámenes",
        "sede": "Externa",
        "tipo": "externa",
        "categoria": "examen",
        "texto": (
            "El Ministerio de Salud recomienda un ayuno mínimo de 8 horas "
            "para exámenes de glicemia y perfil lipídico, permitiendo la "
            "ingesta de agua durante el periodo de ayuno."
        ),
    },
]
