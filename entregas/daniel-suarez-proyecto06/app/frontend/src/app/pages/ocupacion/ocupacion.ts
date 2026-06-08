import { Component, signal, computed, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';   // habilita [(ngModel)] en la plantilla
import { Api, Ocupacion, EspacioEstado, TipoVehiculoItem } from '../../services/api';

@Component({
  selector: 'app-ocupacion',
  imports: [FormsModule],
  templateUrl: './ocupacion.html',
  styleUrl: './ocupacion.css'
})
export class OcupacionComponent {
  private api = inject(Api);

  datos = signal<Ocupacion | null>(null);
  espacios = signal<EspacioEstado[]>([]);   // los 100 espacios para el mapa
  cargando = signal(true);
  error = signal<string | null>(null);

  // ===== Alerta de capacidad (señal derivada de los KPI) =====
  // computed() se recalcula solo cada vez que cambia datos(): al recargar (botón
  // Actualizar) el banner aparece o desaparece sin que escribamos lógica extra.
  nivelAlerta = computed<'normal' | 'critico' | 'lleno'>(() => {
    const pct = this.datos()?.porcentaje_ocupacion ?? 0;
    if (pct >= 100) return 'lleno';
    if (pct >= 90) return 'critico';
    return 'normal';
  });

  // ===== Buscador por tipo (RF5, fusionado desde "Espacios libres") =====
  opciones = signal<{ label: string; id_tipo: number }[]>([]);  // tipos agrupados
  idTipoSeleccionado: number | null = null;                     // enlazado con [(ngModel)]
  // id_espacio de los libres compatibles con el tipo elegido. Set => chequeo O(1) por celda.
  libresCompatibles = signal<Set<number>>(new Set());
  filtroActivo = signal(false);   // ¿hay un tipo aplicado? controla resaltar/atenuar

  constructor() {
    this.cargar();

    // Pedimos los tipos y los transformamos en opciones agrupadas para el dropdown.
    this.api.getTipos().subscribe({
      next: (resp) => this.opciones.set(this.agrupar(resp.datos)),
      error: (err) => console.error(err)
    });
  }

  /** Carga los datos de ocupación. Reutilizable por el botón "Actualizar". */
  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.limpiarFiltro();   // al refrescar, el mapa vuelve a su estado normal

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
      opciones.push({ label: 'Vehículos grandes', id_tipo: losGrandes[0].id_tipo });
    }
    for (const t of tipos) {
      if (!grandes.includes(t.nombre)) {
        opciones.push({ label: t.nombre, id_tipo: t.id_tipo });
      }
    }
    return opciones;
  }

  /** RF5 — busca los espacios libres compatibles y los marca en el mapa. */
  buscar(): void {
    if (this.idTipoSeleccionado === null) {
      this.error.set('Elige un tipo de vehículo primero.');
      return;
    }
    this.error.set(null);
    this.api.getEspaciosLibres(this.idTipoSeleccionado).subscribe({
      next: (resp) => {
        this.libresCompatibles.set(new Set(resp.datos.map((e) => e.id_espacio)));
        this.filtroActivo.set(true);
      },
      error: (err) => {
        console.error(err);
        this.error.set('No se pudieron cargar los espacios libres.');
      }
    });
  }

  /** Quita el resaltado y vuelve el mapa a su estado normal. */
  limpiarFiltro(): void {
    this.idTipoSeleccionado = null;
    this.libresCompatibles.set(new Set());
    this.filtroActivo.set(false);
  }

  /** ¿Este espacio es uno de los libres compatibles encontrados? */
  esCompatible(e: EspacioEstado): boolean {
    return this.libresCompatibles().has(e.id_espacio);
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
