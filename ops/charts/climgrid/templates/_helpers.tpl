{{/* Generate common metadata.labels */}}
{{- define "labels.common" }}
    app: {{ .Chart.Name }}
    # standard chart labels
    chart: {{ .Chart.Name }}-{{ .Chart.Version }}
    release: {{ .Release.Name }}
    heritage: {{ .Release.Service }}
{{- end }}

{{/* Generate common metadata.annotations */}}
{{- define "annotations.common" }}
    commit: {{ .Values.commit }}
{{- end }}
