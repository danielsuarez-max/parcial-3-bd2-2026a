import { Component, signal, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import {
  Api, TipoVehiculoItem, EspacioLibre, Mensualidad, MensualidadIn, TarifaMensual
} from '../../services/api';

type FilaVehiculo = { placa: string; id_tipo: number | null };

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
  // Cupos compatibles con los tipos de vehículo elegidos (se recalcula dinámicamente).
  espaciosLibres = signal<EspacioLibre[]>([]);
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

  // --- Modal de renovación ---
  renovando = signal<Mensualidad | null>(null);
  renovVehiculos = signal<FilaVehiculo[]>([]);
  renovandoId = signal<number | null>(null);

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
    // El cupo ya NO se carga aquí: depende de los tipos elegidos (ver recargarCupos()).
  }

  /** Formatea un número con separador de miles (es-CO): 300000 -> "300.000". */
  fmt(n: number): string {
    return (n ?? 0).toLocaleString('es-CO');
  }

  /** ¿Hay al menos un vehículo con tipo elegido? (para mostrar el cupo). */
  hayTipoSeleccionado(): boolean {
    return this.vehiculos().some((v) => v.id_tipo !== null);
  }

  // ----- Lista dinámica de vehículos -----
  agregarVehiculo(): void {
    this.vehiculos.update((v) => [...v, { placa: '', id_tipo: null }]);
    this.recargarCupos();
  }
  quitarVehiculo(i: number): void {
    this.vehiculos.update((v) => v.filter((_, idx) => idx !== i));
    this.recargarCupos();
  }
  /** El select de tipo de un vehículo cambió: recalcular los cupos compatibles. */
  onVehTipoChange(): void {
    this.recargarCupos();
  }

  /**
   * Recalcula los cupos disponibles = espacios LIBRES compatibles con TODOS los
   * tipos de vehículo elegidos (intersección). Si no hay tipos, lista vacía.
   */
  recargarCupos(): void {
    const tipos = [...new Set(
      this.vehiculos().map((v) => v.id_tipo).filter((t): t is number => t !== null)
    )];
    if (tipos.length === 0) {
      this.espaciosLibres.set([]);
      this.idEspacio = null;
      return;
    }
    // Pedimos los libres por cada tipo y cruzamos (intersección por id_espacio).
    forkJoin(tipos.map((t) => this.api.getEspaciosLibres(t))).subscribe({
      next: (resps) => {
        let inter = resps[0].datos;
        for (let i = 1; i < resps.length; i++) {
          const ids = new Set(resps[i].datos.map((e) => e.id_espacio));
          inter = inter.filter((e) => ids.has(e.id_espacio));
        }
        this.espaciosLibres.set(inter);
        // Si el cupo elegido ya no es compatible, lo reseteamos.
        if (this.idEspacio !== null && !inter.some((e) => e.id_espacio === this.idEspacio)) {
          this.idEspacio = null;
        }
      },
      error: (err) => { console.error(err); this.error.set('No se pudieron cargar los cupos.'); }
    });
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
        this.exito.set(`Mensualidad creada (cupo N° ${resp.numero_espacio}, vence ${resp.fecha_fin}, monto $${this.fmt(resp.monto)}) con placas: ${resp.vehiculos.join(', ')}.`);
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

  // ----- Renovación (modal) -----
  pedirRenovar(m: Mensualidad): void {
    this.error.set(null);
    this.renovando.set(m);
    this.renovVehiculos.set([]);
    // Precargamos los vehículos actuales de esa mensualidad.
    this.api.getVehiculosDeMensualidad(m.id_mensualidad).subscribe({
      next: (resp) => this.renovVehiculos.set(
        resp.datos.map((v) => ({ placa: v.placa, id_tipo: v.id_tipo }))
      ),
      error: (err) => { console.error(err); this.error.set('No se pudieron cargar los vehículos.'); }
    });
  }
  cerrarRenovar(): void { this.renovando.set(null); }

  agregarVehRenov(): void {
    this.renovVehiculos.update((v) => [...v, { placa: '', id_tipo: null }]);
  }
  quitarVehRenov(i: number): void {
    this.renovVehiculos.update((v) => v.filter((_, idx) => idx !== i));
  }

  /** Monto del mes a renovar = suma del valor mensual del set editado. */
  montoRenovacion(): number {
    const mapa = this.valorMesPorTipo();
    return this.renovVehiculos().reduce(
      (suma, v) => suma + (v.id_tipo !== null ? (mapa.get(v.id_tipo) ?? 0) : 0),
      0
    );
  }

  /** Fecha de hoy (la renovación crea un nuevo período que inicia hoy). */
  fechaHoy(): string {
    return new Date().toISOString().slice(0, 10);
  }

  /** Vencimiento del nuevo período = hoy + 1 mes. */
  vencimientoRenovacion(): string {
    const d = new Date();
    const dia = d.getDate();
    d.setMonth(d.getMonth() + 1);
    if (d.getDate() !== dia) d.setDate(0);
    return d.toISOString().slice(0, 10);
  }

  confirmarRenovacion(): void {
    const m = this.renovando();
    if (!m) return;

    const vehs = this.renovVehiculos().map((v) => ({ placa: v.placa.trim().toUpperCase(), id_tipo: v.id_tipo }));
    if (vehs.length === 0 || vehs.some((v) => !v.placa || v.id_tipo === null)) {
      this.error.set('Cada vehículo necesita placa y tipo (al menos uno).'); return;
    }

    this.error.set(null);
    this.renovandoId.set(m.id_mensualidad);
    this.api.renovarMensualidad(m.id_mensualidad, vehs as { placa: string; id_tipo: number }[]).subscribe({
      next: (resp) => {
        this.exito.set(`Mensualidad de ${m.cliente} renovada: nuevo período hasta ${resp.fecha_fin} (monto $${this.fmt(resp.monto)}).`);
        this.renovandoId.set(null);
        this.renovando.set(null);
        this.cargar();
      },
      error: (err) => {
        console.error(err);
        this.error.set(this.extraerError(err));
        this.renovandoId.set(null);
        this.renovando.set(null);
      }
    });
  }

  private extraerError(err: any): string {
    const detail = err?.error?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(' · ');
    return 'Ocurrió un error.';
  }
}
