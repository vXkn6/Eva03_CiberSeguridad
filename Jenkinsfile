pipeline {
    agent any
    options { timestamps() }

    stages {
        stage('Construccion') {
            steps {
                echo 'Construyendo la imagen Docker...'
                sh 'docker build -t securedev-app:latest .'
            }
        }
        stage('Pruebas') {
            steps {
                echo 'Prueba de humo (smoke test)...'
                sh '''
                    docker rm -f securedev-test 2>/dev/null || true
                    docker run -d --name securedev-test -e SECRET_KEY=clave-test securedev-app:latest
                    sleep 6
                    docker exec securedev-test python -c "import urllib.request,sys; r=urllib.request.urlopen('http://localhost:8000/health'); print('Codigo:', r.status); sys.exit(0 if r.status==200 else 1)"
                    echo 'Prueba /health superada'
                    docker rm -f securedev-test
                '''
            }
        }
        stage('Despliegue') {
            steps {
                echo 'Desplegando...'
                sh '''
                    docker rm -f securedev-prod 2>/dev/null || true
                    docker run -d --name securedev-prod --restart unless-stopped -p 8001:8000 -e SECRET_KEY=clave-lab securedev-app:latest
                    sleep 5
                '''
                echo 'Desplegada en http://localhost:8001'
            }
        }
        stage('Seguridad - OWASP ZAP') {
            steps {
                echo 'Analisis de seguridad con OWASP ZAP...'
                sh 'docker run --rm --network host -v /home/kali/zap-reports:/zap/wrk:rw ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t http://localhost:8001 -r zap-report.html -I'
                echo 'Reporte en /home/kali/zap-reports/zap-report.html'
            }
        }
    }
    post {
        success { echo 'PIPELINE COMPLETADO CON EXITO' }
        failure { echo 'EL PIPELINE FALLO - revisar logs' }
    }
}
