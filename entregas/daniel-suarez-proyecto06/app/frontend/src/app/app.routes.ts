import { Routes } from '@angular/router';
import { VehiculosDentroComponent } from './pages/vehiculos-dentro/vehiculos-dentro';

export const routes: Routes = [
  // Ruta vacía ('') -> redirige a /dentro como pantalla de inicio.
  { path: '', redirectTo: 'dentro', pathMatch: 'full' },

  // Cada objeto asocia una URL con el componente que se muestra en el <router-outlet>.
  { path: 'dentro', component: VehiculosDentroComponent },

  // (aquí iremos sumando: 'entrada', 'salida', 'tarifas', 'mensualidades', 'reportes'...)
];
