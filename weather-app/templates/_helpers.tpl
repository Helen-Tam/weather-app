{{- define "weather-app.name" -}}
weather-app
{{- end -}}

{{- define "weather-app.fullname" -}}
{{ include "weather-app.name" . }}
{{- end -}}

