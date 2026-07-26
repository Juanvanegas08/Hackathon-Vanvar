export interface BrochureItem {
  id: string
  ubicacion: string
  proyecto: string
  url: string
  /** Portada (primera página) del flipbook Heyzine. */
  coverImage: string
  precioDesde?: number | null
  precioHasta?: number | null
  fechaEntrega?: string | null
  beneficios?: string[]
  tipologiasResumen?: string | null
  resumen?: string | null
}

/** Brochures enriquecidos desde PDF/OCR + ficha estructurada. */
export const BROCHURES: BrochureItem[] = [
  {
    id: 'versalles',
    ubicacion: 'Ciudadela Maiporé',
    proyecto: 'Versalles',
    url: 'https://heyzine.com/flip-book/be784b0d5c.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/v3/be784b0d5ce02e83deebea0cad55f3a04829ae9c.pdf-thumb.jpg',
    precioDesde: 195200000.0,
    precioHasta: 234700000.0,
    beneficios: ['certificación EDGE', 'entorno amigable con el medio ambiente'],
    tipologiasResumen: 'Apartamento Tipo A (56.29 m²), Apartamento Tipo B (51.41 m²), Apartamento Tipo C (45.05 m²)',
    resumen: 'Versalles es un proyecto en Ciudadela Maiporé, Soacha, con 560 apartamentos en 4 torres de 10 pisos. Cuenta con certificación EDGE, amplias zonas verdes y recreativas, y está cerca de colegios, universidades, centros comerciales y transporte público.',
  },
  {
    id: 'pamplona',
    ubicacion: 'Ciudadela Maiporé',
    proyecto: 'Pamplona',
    url: 'https://heyzine.com/flip-book/c159d5d733.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/v3/c159d5d733b09efe543a524b50f5b60d228a9016.pdf-thumb.jpg',
    precioDesde: 157000000.0,
    precioHasta: 251500000.0,
    beneficios: ['subsidio VIS', 'certificación EDGE'],
    tipologiasResumen: 'Apartamento Tipo A (45.75 m²), Apartamento Tipo B (53.3 m²), Apartamento Tipo C (51.2 m²)',
    resumen: 'Agrupación De Vivienda Pamplona I es un proyecto VIS en Soacha con 488 apartamentos en 12 torres de hasta 13 pisos, con certificación EDGE que garantiza ahorro y sostenibilidad. Ofrece apartamentos funcionales en obra gris, con completas zonas comunes y excelente ubicación cerca ',
  },
  {
    id: 'zarzal',
    ubicacion: 'Ciudadela Maiporé',
    proyecto: 'Zarzal',
    url: 'https://heyzine.com/flip-book/56764c1e33.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/56764c1e33d876d67bcca41b3cda5414f36cb8cf-1.pdf-thumb.jpg',
    precioDesde: 219400000.0,
    precioHasta: 226700000.0,
    beneficios: ['subsidio VIS'],
    tipologiasResumen: 'Apartamento Tipo 1 (43.3 m²), Apartamento Tipo 2',
    resumen: 'Zarzal es un proyecto de apartamentos en obra gris ubicado en Ciudadela Maiporé, Soacha, con 504 unidades distribuidas en 21 torres de 6 pisos. Ofrece subsidio VIS y múltiples amenidades para la vida en familia, cerca de zonas verdes, centros educativos, de salud y transporte púb',
  },
  {
    id: 'la-macarena',
    ubicacion: 'Ciudadela Maiporé',
    proyecto: 'La Macarena',
    url: 'https://heyzine.com/flip-book/b168b2f5ba.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/b168b2f5ba52412aa3cebe352a90c6f95b73fe2c-2.pdf-thumb.jpg',
    precioDesde: 128340000.0,
    precioHasta: 177300000.0,
    beneficios: ['subsidio VIS'],
    resumen: 'Agrupación De Vivienda La Macarena es un proyecto de apartamentos VIS ubicado en Ciudadela Maiporé, Soacha, con precios desde 128.340.000 COP. Cuenta con una ubicación estratégica cerca de colegios, supermercados, universidades y centros comerciales, y ofrece beneficios como subs',
  },
  {
    id: 'mongui',
    ubicacion: 'Ciudadela Maiporé',
    proyecto: 'Monguí',
    url: 'https://heyzine.com/flip-book/866af8f6a6.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/v3/866af8f6a66082c3b8f0fa2654e639bfe413e81f.pdf-thumb.jpg',
    precioDesde: 156470000.0,
    precioHasta: 204194000.0,
    beneficios: ['subsidio VIS'],
    tipologiasResumen: 'Apartamento VIS',
    resumen: 'Agrupación De Vivienda Monguí es un proyecto de apartamentos VIS ubicado en Ciudadela Maiporé, Soacha, que ofrece un entorno integrado con servicios, educación y zonas verdes para una vida tranquila y en comunidad.',
  },
  {
    id: 'bosque-arrayan',
    ubicacion: 'Tocancipá',
    proyecto: 'Bosque de Arrayán',
    url: 'https://heyzine.com/flip-book/7f3c85cf46.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/7f3c85cf4681596d32975f6c19a258742bf481a6-2.pdf-thumb.jpg',
    precioDesde: 168325395.0,
    precioHasta: 224000000.0,
    beneficios: ['subsidio VIS', 'certificación EDGE'],
    resumen: 'Bosque de Arrayán es un proyecto VIS en Tocancipá que ofrece vivienda propia en un entorno tranquilo, seguro y natural. Cuenta con certificación EDGE para eficiencia en agua y energía, promoviendo sostenibilidad y calidad de vida.',
  },
  {
    id: 'bosque-turpial',
    ubicacion: 'Tocancipá',
    proyecto: 'Bosque de Turpial',
    url: 'https://heyzine.com/flip-book/5eec0a2afc.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/5eec0a2afc8e6f34dac69258ab26b67724d528ee.pdf-thumb.jpg',
    precioDesde: 200100000.0,
    precioHasta: 280700000.0,
    beneficios: ['certificación EDGE'],
    tipologiasResumen: 'Apartamento 1 (47 m²), Apartamento 2 (57.52 m²), Apartamento 3 (53.33 m²)',
    resumen: 'Proyecto de vivienda en Tocancipá con apartamentos desde 42.86 m² hasta 57.52 m², entrega en obra gris, con certificación EDGE que garantiza sostenibilidad y eficiencia. Cuenta con amenidades como bicicleteros, parqueaderos y zonas sociales, ubicado cerca de centros comerciales, ',
  },
  {
    id: 'inari',
    ubicacion: 'Chía',
    proyecto: 'Inari',
    url: 'https://heyzine.com/flip-book/8b6615372f.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/v3/8b6615372fffc54771927bc8fe0151d0091d285f.pdf-thumb.jpg',
    precioDesde: 204900000.0,
    precioHasta: 291600000.0,
    beneficios: ['subsidio VIS', 'certificación EDGE'],
    resumen: 'INARI es un proyecto en Chía con subsidio VIS y certificación EDGE, ubicado en una zona de alto crecimiento con excelente infraestructura y cercanía a universidades, centros de salud, centros comerciales y vías principales. Ofrece espacios funcionales ideales para vivir o inverti',
  },
  {
    id: 'reserva-aguayacan',
    ubicacion: 'Girardot',
    proyecto: 'Reserva de Aguayacán',
    url: 'https://heyzine.com/flip-book/aa430852c2.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/aa430852c2281902b828c27bf027af0655989584.pdf-thumb.jpg',
    precioDesde: 175400000.0,
    precioHasta: 239500000.0,
    beneficios: ['subsidio VIS'],
    tipologiasResumen: 'Apartamento Tipo A (46.98 m²), Apartamento Tipo B (38.24 m²), Apartamento Tipo C',
    resumen: 'Proyecto de vivienda VIS en Girardot con 436 apartamentos en 4 torres con ascensor, ubicado en zona de alta valorización cerca de estadio, supermercados y universidades. Apartamentos entregados en obra gris con sugerencias de acabados.',
  },
  {
    id: 'saman',
    ubicacion: 'Ricaurte',
    proyecto: 'Samán',
    url: 'https://heyzine.com/flip-book/1daa8c80c5.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/1daa8c80c56cffb9b0cdd3882c88831412249af9-3.pdf-thumb.jpg',
    precioDesde: 234000000.0,
    precioHasta: 258500000.0,
    beneficios: ['subsidio VIS'],
    resumen: 'AGRUPACIÓN DE VIVIENDA SAMÁN es un proyecto de apartamentos VIS ubicado en Ricaurte, Cundinamarca, con una ubicación estratégica cerca de servicios, zonas naturales y comerciales. Ofrece precios desde 234 millones hasta 258.5 millones de pesos y está en etapa 1.',
  },
  {
    id: 'payande',
    ubicacion: 'Ricaurte',
    proyecto: 'Payandé',
    url: 'https://heyzine.com/flip-book/34ac4d8a9e.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/v3/34ac4d8a9e7889f1c2b73272dac578569521bc24.pdf-thumb.jpg',
    precioDesde: 159471000.0,
    precioHasta: 205206000.0,
    tipologiasResumen: 'Apartamento Tipo 3 (56.86 m²), Apartamento Tipo 4 (44 m²)',
    resumen: 'Agrupacion De Vivienda Payande es un proyecto en Ricaurte, Cundinamarca, con 320 apartamentos en 6 torres de 10 pisos. Ofrece apartamentos en obra gris con 2 habitaciones y 1 baño, ubicado cerca de centros comerciales, hoteles, parques y servicios.',
  },
  {
    id: 'vibo-once',
    ubicacion: 'Ricaurte',
    proyecto: 'Vibo Once',
    url: 'https://heyzine.com/flip-book/d3d1f61d6b.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/v3/d3d1f61d6b986af8f5cfe8fac078aa5ea8c96a02-1.pdf-thumb.jpg',
    precioDesde: 281300000.0,
    precioHasta: 328200000.0,
    beneficios: ['subsidio VIS'],
    tipologiasResumen: 'APARTAMENTO TIPO A (50.44 m²), APARTAMENTO TIPO B2 (42.03 m²)',
    resumen: 'VIBO ONCE es un proyecto VIS ubicado en el centro de Bogotá frente a la futura estación 11 del metro, con 310 apartamentos en torres de 20 pisos. Ofrece buena movilidad, zonas sociales completas y está cerca de hospitales, universidades y parques.',
  },
  {
    id: 'karakali',
    ubicacion: 'Ricaurte',
    proyecto: 'Karakali',
    url: 'https://heyzine.com/flip-book/5083a3d46c.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/5083a3d46c423cf8924b85d5b798e728f3bb50da-4.pdf-thumb.jpg',
    precioDesde: 184720477.0,
    precioHasta: 286054600.0,
    beneficios: ['subsidio VIS'],
    resumen: 'Proyecto Karakalí es un innovador proyecto de apartaestudios en Chapinero, Bogotá, que combina coliving y coworking. Está ubicado estratégicamente cerca de universidades, comercio y vías principales, con subsidio VIS disponible.',
  },
  {
    id: 'araucaria',
    ubicacion: 'Ciudadela Calle 80',
    proyecto: 'Araucaria',
    url: 'https://heyzine.com/flip-book/26d2b013cf.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/26d2b013cf7225db703c2bde5ff96c5f81fb1906-2.pdf-thumb.jpg',
    precioDesde: 562400000.0,
    precioHasta: 1025400000.0,
    tipologiasResumen: 'Apartamento Tipo C (74.36 m²), Apartamento Tipo B (86.93 m²), Apartamento Tipo A1 (105.4 m²)',
    resumen: 'ARAUCARIA es un proyecto ubicado en Ciudadela Calle 80 que ofrece apartamentos con acabados de alta calidad, parqueadero privado y depósito. Cuenta con 252 unidades distribuidas en 4 torres de 7 pisos con ascensor, y amplias zonas sociales para el bienestar de sus residentes.',
  },
  {
    id: 'los-nogales',
    ubicacion: 'Ciudadela Calle 80',
    proyecto: 'Los Nogales',
    url: 'https://heyzine.com/flip-book/9dd9bf814e.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/9dd9bf814e85b164faadfbd527568e36735154d7-1.pdf-thumb.jpg',
    precioDesde: 511500000.0,
    precioHasta: 803480000.0,
    tipologiasResumen: 'Tipo A (67 m²), Tipo A (74 m²)',
    resumen: 'Los Nogales es un proyecto ubicado en Ciudadela Calle 80 que ofrece apartamentos con terminaciones de alta calidad, parqueadero privado y depósito. Cuenta con 168 unidades distribuidas en 3 torres de 7 pisos con ascensor, cerca de colegios, centros médicos, centros comerciales y ',
  },
  {
    id: 'verde-esperanza',
    ubicacion: 'Ubaté',
    proyecto: 'Verde Esperanza',
    url: 'https://heyzine.com/flip-book/ea1997d7ae.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/v3/ea1997d7ae6f96d3124eea9a740cdd3a2ea401e2-3.pdf-thumb.jpg',
    precioDesde: 149400000.0,
    precioHasta: 179300000.0,
    beneficios: ['subsidio VIS'],
    tipologiasResumen: 'APARTAMENTO TIPO A (49.53 m²)',
    resumen: 'Verde Esperanza El Dorado es un proyecto en Ubaté con 440 apartamentos en 22 torres de 5 pisos, rodeado de amplias zonas verdes y espacios para la recreación. Los apartamentos se entregan en obra gris y cuentan con 2 habitaciones. El proyecto ofrece subsidio VIS y está cerca de c',
  },
  {
    id: 'multiproyecto',
    ubicacion: 'Multiproyecto',
    proyecto: 'Multiproyecto',
    url: 'https://heyzine.com/flip-book/1de36642fc.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/v3/1de36642fc03010e335a632401ce2fad82df2f67-1.pdf-thumb.jpg',
    resumen: 'Te acompañamos con asesoría y soluciones integrales de vivienda para cumplir tu sueño. tu proyectode vida Tener vivienda propia, Proyecto Subsidio Crédito Seguro = Vivienda propia Contenido: Nuestros proyectos Bogotá, Centro Vibo once Ricaurte, Cundinamarca Payandé Samán Girardot',
  },
  {
    id: 'revista',
    ubicacion: 'Multiproyecto',
    proyecto: 'Revista',
    url: 'https://heyzine.com/flip-book/1cdf69c6d5.html',
    coverImage: 'https://cdnc.heyzine.com/files/uploaded/1cdf69c6d5e12951de6af1a9403eccadc8e80f41-2.pdf-thumb.jpg',
    resumen: 'Te acompañamos con asesoría y soluciones integrales de vivienda para cumplir tu sueño. tu proyectode vida Un espacio para vivir… y para comenzar lo que siempre soñaste, Chía /gid00001/gid00015/gid00042/gid00034/gid00028/gid00039/gid00032/gid00046 /gid00013/gid00042/gid00046 /gid0',
  },
]

const normalizeProjectKey = (value: string) =>
  value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')

/** Resuelve brochure Heyzine por id/nombre de proyecto. */
export const findBrochureForProject = (input: {
  projectId?: string | null
  canonicalId?: string | null
  projectName?: string | null
  brochureUrl?: string | null
}): BrochureItem | null => {
  if (input.brochureUrl) {
    const byUrl = BROCHURES.find((item) => item.url === input.brochureUrl)
    if (byUrl) return byUrl
  }

  const keys = [input.projectId, input.canonicalId, input.projectName]
    .filter((value): value is string => Boolean(value?.trim()))
    .map(normalizeProjectKey)

  for (const key of keys) {
    const match = BROCHURES.find((item) => {
      const idKey = normalizeProjectKey(item.id)
      const nameKey = normalizeProjectKey(item.proyecto)
      return (
        key === idKey ||
        key === nameKey ||
        key.includes(idKey) ||
        idKey.includes(key) ||
        key.includes(nameKey) ||
        nameKey.includes(key)
      )
    })
    if (match) return match
  }

  return null
}
