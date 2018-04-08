{{/* Generate common metadata.labels */}}
{{- define "labels.common" }}
    app: {{ .Chart.Name }}
    environment: {{ .Values.environment }}
    chart: {{ .Chart.Name }}-{{ .Chart.Version }}
    release: {{ .Release.Name }}
    heritage: {{ .Release.Service }}
{{- end }}

{{/* Generate common metadata.annotations */}}
{{- define "annotations.common" }}
    commit: {{ .Values.commit }}
{{- end }}

{{/* Env vars for climgrid web/worker containers */}}
{{- define "climgrid.env" }}
            - name: REDIS_URI
              value: redis://$({{ .Values.redis.fullnameOverride | upper | replace "-" "_" }}_SERVICE_HOST):6379/0
{{- end }}
