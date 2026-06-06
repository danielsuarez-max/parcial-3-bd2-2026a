import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-root',
  // RouterOutlet = el "hueco" donde se enchufa la vista de cada ruta.
  // RouterLink = para que los enlaces del menú cambien la ruta sin recargar.
  // RouterLinkActive = resalta el enlace de la vista que se está viendo.
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {}
