import { ApplicationConfig, provideBrowserGlobalErrorListeners, LOCALE_ID } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { registerLocaleData } from '@angular/common';
import localeEsCo from '@angular/common/locales/es-CO';

import { routes } from './app.routes';

// Registramos el locale Colombia: el pipe `number` usa punto de miles ($150.000)
// y las fechas (`| date`) se muestran en español.
registerLocaleData(localeEsCo);

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(),     // habilita peticiones HTTP en toda la app
    { provide: LOCALE_ID, useValue: 'es-CO' }
  ]
};
