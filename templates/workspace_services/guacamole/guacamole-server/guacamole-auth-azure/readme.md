# Guacamole Authorization Extension

This extension is built (maven) and is placed inside the extension directory.
Guacamole tries to authorize using all the given extensions.
Read more [here](https://guacamole.apache.org/doc/gug/guacamole-ext.html).

## TRE Authorization extension

This extension works in the following manner:

1. recieves the acccess token from the header : x-access-token
2. The extension call the project api to get the user's vm list
3. When connect request is made, the extension call the project api to get the password to the selected vm and inject it into the Guacamole configurations.