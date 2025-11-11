# Algoritmo_test

Prueba tecbuca para Algoritmo, el cual es un proyecto de backend modular que se realiza en FastAPI con el fin de conectarse a la APÏ de Gmail y poder analizar correos archivos PDF, poder extraer los productos del correo y clasificarlos por "Purchase order" (PO) o por "Quote" (QUOTE), en el cual se tendran etiquetas en el gmail de prueba que mas adelante se explicara.

#   Puntos de Vista a tener en cuenta.

-El proyecto se puede correr mediante Docker, sin necesidad de instalar los requirements directamente en el dispositivo que se esté usando.
-El proyecto se puede correr de cero, o en su caso adicionalmente el proyecto esta subido a Railway, por tal razon 




#Crear cuenta y enlazar con Google Cloud
-Primero creamos una cuenta gmail de prueba a la cual se le va a aplicar el servicio de backend de la prueba tecnica.
-Luego se dirige a Google Cloud y en este apartado nos vamos a la parte de APIS y servicios, directamente hacia pantalla de consentimiento de 0Auth y creamos una credencial de json.
-Al momento de estar creando y configurando el proyecto, marcamos el nombre de la aplicacion, seleccionamos el correo de prueba que estamos usando, en publico lo dejamos externo y al final aceptamos las politicas del uso de los servicios de las Apis de Google y creamos el proyecto.
-Ahora se procede a crear el ID de cliente de OAuth, seleccionamos el tipo de aplicacion web, y descargamos el JSON del id de cliente y lo agregamos al proyecto.
-Ahora vamos al apartado de Apis y servicios en "biblioteca" y buscamos Gmail API y lo habilitamos.
-El siguiente paso es volver a Apis y servicios en el apartado de "Pantalla de consentimiento de OAuth" y nos dirigimos a "Acceso a los datos" y agregamos los permisos de gmail.readonly y de gmail.modify y se guardan estos permisos o "Scopes"
-Con esto activo corremos el ocdigo y nos vamos a la direccion "http://localhost:8000/emails/auth/login" y ahi nos sale el url de la autenticacion donde se aceptan todos los permisos.
-Tambien tener en cuenta que en el tipo de usuario, en usuarios de prueba se agrega el correo que estamos usando.

