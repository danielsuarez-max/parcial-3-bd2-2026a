import { Component, signal, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Api, TipoVehiculoItem, EspacioLibre } from '../../services/api';

@Component({
  selector: 'app-espacios-libres',
  imports: [FormsModule],     // FormsModule habilita [(ngModel)] en la plantilla
  templateUrl: './espacios-libres.html',
  styleUrl: './espacios-libres.css'
})
export class EspaciosLibresComponent {
  private api = inject(Api);

  tipos = signal<TipoVehiculoItem[]>([]);   // opciones del dropdown
  idTipoSeleccionado: number | null = null;  // valor enlazado con [(ngModel)]

  espacios = signal<EspacioLibre[]>([]);
  cargando = signal(false);
  error = signal<string | null>(null);
  buscado = signal(false);   // ¿ya se hizo al menos una búsqueda?

  constructor() {
    // Al abrir la vista, llenamos el dropdown con los tipos del backend.
    this.api.getTipos().subscribe({
      next: (resp) => this.tipos.set(resp.datos),
      error: (err) => { console.error(err); this.error.set('No se pudieron cargar los tipos.'); }
    });
  }

  buscar(): void {
    if (this.idTipoSeleccionado === null) {
      this.error.set('Elige un tipo de vehículo primero.');
      return;
    }
    this.cargando.set(true);
    this.error.set(null);
    this.api.getEspaciosLibres(this.idTipoSeleccionado).subscribe({
      next: (resp) => {
        this.espacios.set(resp.datos);
        this.buscado.set(true);
        this.cargando.set(false);
      },
      error: (err) => {
        console.error(err);
        this.error.set('No se pudieron cargar los espacios libres.');
        this.cargando.set(false);
      }
    });
  }
}
