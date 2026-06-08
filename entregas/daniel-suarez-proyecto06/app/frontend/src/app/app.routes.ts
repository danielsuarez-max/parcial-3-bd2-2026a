import { Routes } from '@angular/router';
import { VehiculosDentroComponent } from './pages/vehiculos-dentro/vehiculos-dentro';
import { OcupacionComponent } from './pages/ocupacion/ocupacion';
import { RegistrarEntradaComponent } from './pages/registrar-entrada/registrar-entrada';
import { HistorialComponent } from './pages/historial/historial';
import { TarifasComponent } from './pages/tarifas/tarifas';
import { MensualidadesComponent } from './pages/mensualidades/mensualidades';

export const routes: Routes = [
  // Ruta vacía ('') -> redirige a /dentro como pantalla de inicio.
  { path: '', redirectTo: 'dentro', pathMatch: 'full' },

  // Cada objeto asocia una URL con el componente que se muestra en el <router-outlet>.
  { path: 'dentro', component: VehiculosDentroComponent },
  { path: 'ocupacion', component: OcupacionComponent },
  // "Espacios libres" se fusionó dentro de Ocupación: redirigimos para no romper marcadores.
  { path: 'espacios-libres', redirectTo: 'ocupacion', pathMatch: 'full' },
  { path: 'entrada', component: RegistrarEntradaComponent },
  { path: 'historial', component: HistorialComponent },
  { path: 'tarifas', component: TarifasComponent },
  { path: 'mensualidades', component: MensualidadesComponent },

  // (aquí iremos sumando: 'entrada', 'salida', 'tarifas', 'mensualidades', 'reportes'...)
];
