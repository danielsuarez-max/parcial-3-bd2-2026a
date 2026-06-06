import { Routes } from '@angular/router';
import { VehiculosDentroComponent } from './pages/vehiculos-dentro/vehiculos-dentro';
import { OcupacionComponent } from './pages/ocupacion/ocupacion';
import { EspaciosLibresComponent } from './pages/espacios-libres/espacios-libres';
import { RegistrarEntradaComponent } from './pages/registrar-entrada/registrar-entrada';
import { HistorialComponent } from './pages/historial/historial';

export const routes: Routes = [
  // Ruta vacía ('') -> redirige a /dentro como pantalla de inicio.
  { path: '', redirectTo: 'dentro', pathMatch: 'full' },

  // Cada objeto asocia una URL con el componente que se muestra en el <router-outlet>.
  { path: 'dentro', component: VehiculosDentroComponent },
  { path: 'ocupacion', component: OcupacionComponent },
  { path: 'espacios-libres', component: EspaciosLibresComponent },
  { path: 'entrada', component: RegistrarEntradaComponent },
  { path: 'historial', component: HistorialComponent },

  // (aquí iremos sumando: 'entrada', 'salida', 'tarifas', 'mensualidades', 'reportes'...)
];
