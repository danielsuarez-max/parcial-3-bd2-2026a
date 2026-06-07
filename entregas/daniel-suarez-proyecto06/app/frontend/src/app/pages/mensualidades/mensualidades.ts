import { Component, signal, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  Api, TipoVehiculoItem, EspacioEstado, Mensualidad, MensualidadIn, TarifaMensual
} from '../../services/api';

@Component({
  selector: 'app-mensualidades',
  imports: [FormsModule],
  templateUrl: './mensualidades.html',
  styleUrl: './mensualidades.css'
})
export class MensualidadesComponent {
  private api = inject(Api);

  // --- Lista ---
  mensualidades = signal<Mensualidad[]>([]);
  cargando = signal(true);

  // --- Catálogos para el formulario ---
  tipos = signal<TipoVehiculoItem[]>([]);
  espaciosLibres = signal<EspacioEstado[]>([]);
  // Valor mensual por tipo (id_tipo -> valor_mes), para calcular el monto en pantalla.
  valorMesPorTipo = signal<Map<number, number>>(new Map());

  // --- Formulario de alta ---
  documento = '';
  nombre = '';
  telefono = '';
  email = '';
  idEspacio: number | null = null;
  fechaInicio = '';
  // Lista dinámica de vehículos (empieza con una fila vacía)
  vehiculos = signal<{ placa: string; id_tipo: number | null }[]>([{ placa: '', id_tipo: null }]);

  enviando = signal(false);
  exito = signal<string | null>(null);
  error = signal<string | null>(null);

  // --- Modal de cancelación ---
  cancelando = signal<Mensualidad | null>(null);
  cancelandoId = signal<number | null>(null);

  constructor() {
    this.cargar();
    this.api.getTipos().subscribe({
      next: (resp) => this.tipos.set(resp.datos),
      error: (err) => console.error(err)
    });
    // Catálogo de valor mensual por tipo -> lo guardamos como Map para sumar rápido.
    this.api.getTarifasMensuales().subscribe({
      next: (resp) => {
        const mapa = new Map<number, number>();
        for (const t of resp.datos) mapa.set(t.id_tipo, Number(t.valor_mes));
        this.valorMesPorTipo.set(mapa);
      },
      error: (err) => console.error(err)
    });
  }

  /** Monto estimado = suma del valor mensual de los vehículos con tipo elegido. */
  montoEstimado(): number {
    const mapa = this.valorMesPorTipo();
    return this.vehiculos().reduce(
      (suma, v) => suma + (v.id_tipo !== null ? (mapa.get(v.id_tipo) ?? 0) : 0),
      0
    );
  }

  /** Fecha fin estimada = fecha inicio + 1 mes (se calcula también en el backend). */
  fechaFinEstimada(): string {
    if (!this.fechaInicio) return '—';
    const d = new Date(this.fechaInicio + 'T00:00:00');
    const dia = d.getDate();
    d.setMonth(d.getMonth() + 1);
    // Si el mes destino no tiene ese día, JS se pasa de mes: lo corregimos.
    if (d.getDate() !== dia) d.setDate(0);
    return d.toISOString().slice(0, 10);
  }

  cargar(): void {
    this.cargando.set(true);
    this.api.getMensualidades().subscribe({
      next: (resp) => { this.mensualidades.set(resp.datos); this.cargando.set(false); },
      error: (err) => { console.error(err); this.error.set('No se pudieron cargar las mensualidades.'); this.cargando.set(false); }
    });
    // Espacios libres para el dropdown del cupo (filtramos del mapa completo).
    this.api.getEspacios().subscribe({
      next: (resp) => this.espaciosLibres.set(resp.datos.filter((e) => e.estado === 'LIBRE')),
      error: (err) => console.error(err)
    });
  }

  // ----- Lista dinámica de vehículos -----
  agregarVehiculo(): void {
    this.vehiculos.update((v) => [...v, { placa: '', id_tipo: null }]);
  }
  quitarVehiculo(i: number): void {
    this.vehiculos.update((v) => v.filter((_, idx) => idx !== i));
  }

  // ----- Crear -----
  crear(): void {
    this.exito.set(null);
    this.error.set(null);

    if (!this.documento.trim() || !this.nombre.trim()) {
      this.error.set('Documento y nombre del cliente son obligatorios.'); return;
    }
    if (this.idEspacio === null)  { this.error.set('Elige un cupo (espacio).'); return; }
    if (!this.fechaInicio) { this.error.set('Indica la fecha de inicio.'); return; }

    // Validamos y normalizamos los vehículos (placa no vacía + tipo elegido).
    const vehs = this.vehiculos().map((v) => ({ placa: v.placa.trim().toUpperCase(), id_tipo: v.id_tipo }));
    if (vehs.some((v) => !v.placa || v.id_tipo === null)) {
      this.error.set('Cada vehículo necesita placa y tipo.'); return;
    }

    const m: MensualidadIn = {
      cliente: {
        documento: this.documento.trim(),
        nombre_completo: this.nombre.trim(),
        telefono: this.telefono.trim() || null,
        email: this.email.trim() || null,
      },
      id_espacio: this.idEspacio,
      fecha_inicio: this.fechaInicio,
      vehiculos: vehs as { placa: string; id_tipo: number }[],
    };

    this.enviando.set(true);
    this.api.postMensualidad(m).subscribe({
      next: (resp) => {
        this.exito.set(`Mensualidad creada (cupo N° ${resp.numero_espacio}, vence ${resp.fecha_fin}, monto $${resp.monto}) con placas: ${resp.vehiculos.join(', ')}.`);
        this.enviando.set(false);
        this.limpiar();
        this.cargar();
      },
      error: (err) => { console.error(err); this.error.set(this.extraerError(err)); this.enviando.set(false); }
    });
  }

  private limpiar(): void {
    this.documento = ''; this.nombre = ''; this.telefono = ''; this.email = '';
    this.idEspacio = null; this.fechaInicio = '';
    this.vehiculos.set([{ placa: '', id_tipo: null }]);
  }

  // ----- Cancelación (modal) -----
  pedirCancelar(m: Mensualidad): void { this.cancelando.set(m); }
  cerrarCancelar(): void { this.cancelando.set(null); }

  confirmarCancelacion(): void {
    const m = this.cancelando();
    if (!m) return;
    this.error.set(null);
    this.cancelandoId.set(m.id_mensualidad);
    this.api.cancelarMensualidad(m.id_mensualidad).subscribe({
      next: () => {
        this.exito.set(`Mensualidad de ${m.cliente} cancelada; cupo N° ${m.numero_espacio} liberado.`);
        this.cancelandoId.set(null);
        this.cancelando.set(null);
        this.cargar();
      },
      error: (err) => {
        console.error(err);
        this.error.set(this.extraerError(err));
        this.cancelandoId.set(null);
        this.cancelando.set(null);
      }
    });
  }

  // ----- Vencer expiradas -----
  vencer(): void {
    this.exito.set(null); this.error.set(null);
    this.api.vencerExpiradas().subscribe({
      next: (resp) => { this.exito.set(`Barrido completado: ${resp.mensualidades_vencidas} mensualidad(es) vencida(s).`); this.cargar(); },
      error: (err) => { console.error(err); this.error.set('No se pudo ejecutar el barrido.'); }
    });
  }

  private extraerError(err: any): string {
    const detail = err?.error?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(' · ');
    return 'Ocurrió un error.';
  }
}
