import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { ToastsComponent } from './components/toasts/toasts';

@Component({
  selector: 'app-root',
  // RouterOutlet = el "hueco" donde se enchufa la vista de cada ruta.
  // RouterLink = para que los enlaces del menú cambien la ruta sin recargar.
  // RouterLinkActive = resalta el enlace de la vista que se está viendo.
  imports: [RouterOutlet, RouterLink, RouterLinkActive, ToastsComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {}
