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

  // Opciones del dropdown ya AGRUPADAS (los 3 grandes colapsados en una sola).
  opciones = signal<{ label: string; id_tipo: number }[]>([]);
  idTipoSeleccionado: number | null = null;  // valor enlazado con [(ngModel)]

  espacios = signal<EspacioLibre[]>([]);
  cargando = signal(false);
  error = signal<string | null>(null);
  buscado = signal(false);   // ¿ya se hizo al menos una búsqueda?

  constructor() {
    // Al abrir la vista, pedimos los tipos y los transformamos en opciones agrupadas.
    this.api.getTipos().subscribe({
      next: (resp) => this.opciones.set(this.agrupar(resp.datos)),
      error: (err) => { console.error(err); this.error.set('No se pudieron cargar los tipos.'); }
    });
  }

  /**
   * Carro, Camioneta y Camión comparten los espacios grandes (1-70), así que
   * consultarlos por separado es redundante: los unimos en una sola opción.
   * Mandamos el id_tipo de cualquiera de ellos (devuelven los mismos espacios).
   */
  private agrupar(tipos: TipoVehiculoItem[]): { label: string; id_tipo: number }[] {
    const grandes = ['Carro', 'Camioneta', 'Camión'];
    const opciones: { label: string; id_tipo: number }[] = [];

    const losGrandes = tipos.filter((t) => grandes.includes(t.nombre));
    if (losGrandes.length > 0) {
      opciones.push({
        label: 'Vehículos grandes',
        id_tipo: losGrandes[0].id_tipo,   // representante del grupo
      });
    }
    // El resto (Moto, Bicicleta...) se agrega tal cual.
    for (const t of tipos) {
      if (!grandes.includes(t.nombre)) {
        opciones.push({ label: t.nombre, id_tipo: t.id_tipo });
      }
    }
    return opciones;
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
