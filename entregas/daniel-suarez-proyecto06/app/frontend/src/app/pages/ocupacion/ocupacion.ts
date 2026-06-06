import { Component, signal, inject } from '@angular/core';
import { Api, Ocupacion, EspacioEstado } from '../../services/api';

@Component({
  selector: 'app-ocupacion',
  imports: [],
  templateUrl: './ocupacion.html',
  styleUrl: './ocupacion.css'
})
export class OcupacionComponent {
  private api = inject(Api);

  datos = signal<Ocupacion | null>(null);
  espacios = signal<EspacioEstado[]>([]);   // los 100 espacios para el mapa
  cargando = signal(true);
  error = signal<string | null>(null);

  constructor() {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);

    // Pedimos los totales (KPI)...
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

    // ...y en paralelo, el detalle de cada espacio para el mapa.
    this.api.getEspacios().subscribe({
      next: (resp) => this.espacios.set(resp.datos),
      error: (err) => console.error(err)
    });
  }

  /** Texto que se muestra al pasar el mouse sobre un cuadro. */
  tooltip(e: EspacioEstado): string {
    if (e.estado === 'OCUPADO') {
      return 'Ocupado' + (e.placa ? ` · ${e.placa}` : '');
    }
    if (e.estado === 'RESERVADO') {
      return 'Reservado' + (e.reservado_para ? ` · ${e.reservado_para}` : '');
    }
    return 'Libre';
  }
}
