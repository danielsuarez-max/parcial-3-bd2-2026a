import { Component, signal, inject } from '@angular/core';
import { Api, Ocupacion } from '../../services/api';

@Component({
  selector: 'app-ocupacion',
  imports: [],
  templateUrl: './ocupacion.html',
  styleUrl: './ocupacion.css'
})
export class OcupacionComponent {
  private api = inject(Api);

  datos = signal<Ocupacion | null>(null);
  cargando = signal(true);
  error = signal<string | null>(null);

  constructor() {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.getOcupacion().subscribe({
      next: (resp) => {
        this.datos.set(resp);
        this.cargando.set(false);
      },
      error: (err) => {
        console.error(err);
        this.error.set('No se pudo cargar la ocupación.');
        this.cargando.set(false);
      }
    });
  }
}
