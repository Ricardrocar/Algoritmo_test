# Algoritmo_test

Prueba tecnica para Algoritmo, el cual es un proyecto de backend modular que se realiza en FastAPI con el fin de conectarse a la APÏ de Gmail y poder analizar correos archivos PDF, poder extraer los productos del correo y clasificarlos por "Purchase order" (PO) o por "Quote" (QUOTE), en el cual se tendran etiquetas en el gmail de prueba que mas adelante se explicara.

#   Puntos de Vista a tener en cuenta.

-El proyecto se puede correr mediante Docker, sin necesidad de instalar los requirements directamente en el dispositivo que se esté usando.
-En el parrafo final del ReadMe estan los dos comandos que se pueden utilizar para correr el proyecto.
-Dejo el enlace a mi perfil de github, no es el primer proyecto que manejo en este programa y conozco tambien mas lenguajes o ver las estadisticas que manejo  https://github.com/Ricardrocar


##Crear cuenta y enlazar con Google Cloud

-Primero creamos una cuenta gmail de prueba a la cual se le va a aplicar el servicio de backend de la prueba tecnica.

-Luego se dirige a Google Cloud y en este apartado nos vamos a la parte de APIS y servicios, directamente hacia pantalla de consentimiento de 0Auth y creamos una credencial de json.

-Al momento de estar creando y configurando el proyecto, marcamos el nombre de la aplicacion, seleccionamos el correo de prueba que estamos usando, en publico lo dejamos externo y al final aceptamos las politicas del uso de los servicios de las Apis de Google y creamos el proyecto.

-Ahora se procede a crear el ID de cliente de OAuth, seleccionamos el tipo de aplicacion web, y descargamos el JSON del id de cliente y lo agregamos al proyecto.

-Ahora vamos al apartado de Apis y servicios en "biblioteca" y buscamos Gmail API y lo habilitamos.

-El siguiente paso es volver a Apis y servicios en el apartado de "Pantalla de consentimiento de OAuth" y nos dirigimos a "Acceso a los datos" y agregamos los permisos de gmail.readonly y de gmail.modify y se guardan estos permisos o "Scopes"

-Con esto activo corremos el ocdigo y nos vamos a la direccion "http://localhost:8000/emails/auth/login" y ahi nos sale el url de la autenticacion donde se aceptan todos los permisos.

-Tambien tener en cuenta que en el tipo de usuario, en usuarios de prueba se agrega el correo que estamos usando.

Luego para el token.json y los permisos de modificacion y lectura de los correos, iniciamos el programa y nos dirigimos a la siguiente seccion "http://localhost:8000/emails/auth/login" y aqui procedemos a copiar el auth_url y dirigirnos hacia ese link para aprobar los permisos y se genere el token.json que nos permite ingresar a "http://localhost:8000/emails/analyze" donde podemos analizar los json de los correos que van llegando y en ese momento el correo que acaba de llegar se organizara dependiendo del contenido que posea, en las etiquetas (PO) o (QUOTE) segun corresponda, moviendose de la vista principal en la que estaba.

Apenas en este mismo endpoint se clasifique el tipo de consulta o resumen "http://localhost:8000/emails/analyze" se descarga el JSON, el CSV y un XSLX automaticamente con los datos del correo que acaba de llegar en un archivo .zip


Por ultimo, el proyecto como mencione anteriormente lo estoy corriendo en docker, con el comando "docker-compose up --build" lo que nos permite beneficios en no tener que instalar los requirements directamente en nuestro dispositivo, pero en caso de que se desee instalar y corrar tal cual tambien se puede mediante el comando "python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000".
