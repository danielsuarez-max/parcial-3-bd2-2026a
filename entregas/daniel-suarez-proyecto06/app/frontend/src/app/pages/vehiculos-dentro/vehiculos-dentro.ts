import { Component, signal, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Api, VehiculoDentro } from '../../services/api';

@Component({
  selector: 'app-vehiculos-dentro',
  imports: [DatePipe],
  templateUrl: './vehiculos-dentro.html',
  styleUrl: './vehiculos-dentro.css'
})
export class VehiculosDentroComponent {
  private api = inject(Api);

  vehiculos = signal<VehiculoDentro[]>([]);
  cargando = signal(true);
  error = signal<string | null>(null);

  constructor() {
    this.cargar();
  }

  /** Pide al backend la lista de vehículos dentro. Reutilizable por el botón "Actualizar". */
  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.getVehiculosDentro().subscribe({
      next: (resp) => {
        this.vehiculos.set(resp.datos);
        this.cargando.set(false);
      },
      error: (err) => {
        console.error(err);
        this.error.set('No se pudo conectar con el backend. ¿Está corriendo en el puerto 8001?');
        this.cargando.set(false);
      }
    });
  }
}
