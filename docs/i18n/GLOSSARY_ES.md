# Spanish glossary (draft for review)

Plain Latin-American Spanish. Address the reader with **usted** in instructions; prefer courteous, direct wording and avoid *tú*. Use the same term consistently across screens. These are translation suggestions, not proof that Spanish UI is available or shipped. Review legal/consent wording with the product owner before use.

| English concept | Spanish (Latin America) | Register / usage note |
|---|---|---|
| personal information | datos personales | Plain, common privacy term. |
| personal details | datos personales | Prefer this over a literal translation of “details.” |
| information | información | Use when the source is broad or nontechnical. |
| data | datos | Use for information stored or processed by the app. |
| privacy | privacidad | Standard everyday term. |
| privacy request | solicitud de privacidad | Explain the specific action nearby if needed. |
| deletion request | solicitud de eliminación | Avoid implying universal or guaranteed removal. |
| delete | eliminar | Use for a requested action; avoid *borrar* in formal consent text. |
| remove | quitar / eliminar | Prefer *eliminar* for data; *quitar* for removing an item from a list. |
| stop selling | dejar de vender | Plain phrase; retain the object (“sus datos”) where context is unclear. |
| opt out | solicitar que dejen de vender sus datos | Avoid a technical loan translation. |
| data broker | empresa que vende datos personales | Plain explanation; avoid unfamiliar literal calques. |
| people-search site | sitio web de búsqueda de personas | Keep as a clear descriptive phrase. |
| listing | registro / publicación | Use *registro* for an entry in a site's records; *publicación* for displayed content. |
| possible match | posible coincidencia | Keep uncertainty explicit. A match is a prompt for the person to review, not a claim that the listing belongs to them. |
| “Is this you?” | ¿Es usted? | Short, respectful usted-form heading. It asks the person to decide; it does not assert identity. |
| “Yes, this is me” | Sí, soy yo | First-person answer for the person to choose; do not translate as the app confirming identity. |
| “No, this is not me” | No, no soy yo | First-person answer. Preserve that choosing No stops requests for this listing. |
| confirm it's you / confirm identity | confirmar si es usted | Plain usted form for explanatory text. The person's answer is the confirmation; a possible match alone is not. |
| search result | resultado de búsqueda | Common wording. |
| website | sitio web | Use consistently; *página web* may mean a single page. |
| site | sitio | In UI, *sitio web* may be clearer on first mention. |
| account | cuenta | Plain, familiar term. |
| setup | configuración | Use for initial setup and settings. |
| setup file | archivo de configuración | Avoid implying that it is an online account. |
| family setup file | archivo de configuración familiar | Keep literal enough to distinguish the file's purpose. |
| profile | perfil | Explain whose profile if several people are listed. |
| person | persona | Prefer this over labels that assume a family role. |
| name | nombre | Plain term. |
| first name | nombre | If needed, clarify “nombre de pila.” |
| middle name | segundo nombre | Add “si tiene” for optional fields. |
| last name | apellido | Common across Latin America. |
| earlier name | nombre anterior | Use for names previously used. |
| maiden name | apellido de soltera | Use only when the source specifically means this. |
| nickname | apodo | Familiar and neutral. |
| address | domicilio | In a form, use *dirección* if that is the established product term; be consistent. |
| old address | domicilio anterior | Keep distinct from current address. |
| city | ciudad | Plain term. |
| state | estado | For U.S. state field, clarify country-specific context. |
| phone number | número de teléfono | Standard wording. |
| email address | dirección de correo electrónico | In tight labels, *correo electrónico* can suffice. |
| birth year | año de nacimiento | Do not shorten to “edad.” |
| relative | familiar | Neutral and clear. |
| consent | consentimiento | Legal term; owner review before publication. |
| permission | permiso | Use for ordinary permission; distinguish formal consent where needed. |
| signed permission | permiso firmado | Plain wording. |
| authorization | autorización | Formal but widely understood. |
| authorized agent | representante autorizado | Explain plainly on first use. |
| legal guardian | tutor legal | Common legal term; verify jurisdictional wording. |
| parent | padre, madre o persona progenitora | Choose inclusive concise wording appropriate to the final UI. |
| sign | firmar | Direct and familiar. |
| signature | firma | Standard form label. |
| agree | aceptar | Use for an action button; in a statement, *estoy de acuerdo*. |
| approve | aprobar | Familiar; explain what approval sends or changes. |
| approval | aprobación | Use consistently with *aprobar*. In Free My ID, distinguish approval to send an email from answering whether a listing is the person's; the latter is *confirmar que se trata de usted*. |
| pause | pausar | Plain verb. |
| practice mode | modo de práctica | Safety-critical: practice mode still searches sites but sends no removal requests. Do not imply that no data is sent anywhere or that requests are merely waiting for approval. |
| In practice mode no removal requests go out. | En el modo de práctica no se envían solicitudes de eliminación. | Review-card consequence copy (`src/freemyid/wizard/dashboard.py:130-131`). Practice mode still searches sites; don't imply that no information is sent anywhere. When addressing the reader, keep usted form (for example, “usted puede revisar los resultados”); this impersonal sentence needs no pronoun. |
| Practice mode: Free My ID is looking for your listings, but no removal requests go out until you say so. | Modo de práctica: Free My ID busca sus anuncios, pero no envía solicitudes de eliminación hasta que usted lo indique. | Suggested wording for the dashboard banner (`src/freemyid/wizard/dashboard.py:237-239`). Keep the contrast precise: searches continue, while removal requests do not go out until the person chooses. Use usted form; this is a translator suggestion, not shipped Spanish UI. |
| Free My ID will look for your listings, but no removal requests go out until you turn that on in Settings. | Free My ID buscará sus anuncios, pero no enviará solicitudes de eliminación hasta que usted active esa opción en Configuración. | Suggested wording for the setup-screen practice notice (`src/freemyid/wizard/ui.py:341-343`). Practice mode still searches sites. Keep the user's action and Settings location explicit; use usted form. Translator suggestion only; Spanish UI is not shipped. |
| The first time can take up to a minute. | La primera vez, puede tardar hasta un minuto. | Suggested Windows first-start wording (`packaging/windows/splash_win.py:20-21`; `packaging/windows/freemyid.iss:34-35,56`). Calm expectation-setting; do not imply every launch takes this long. Translator suggestion only. |
| Please wait; there is no need to click it again. | Espere; no hace falta que vuelva a hacer clic. | Suggested slow-start message after 120 seconds (`packaging/windows/splash_win.py:22-23`). Reassure the reader without suggesting the app has failed; use usted form. Translator suggestion only. |
| real requests | solicitudes reales | Pair with an explanation before enabling. |
| request | solicitud | For privacy requests; use *pedido* only in informal regional copy. |
| email | correo electrónico | In short navigation, *Correos* may be acceptable after review. |
| inbox | bandeja de entrada | Standard phrase. |
| outbox | correos pendientes de aprobación | Prefer an explanatory UI label over a technical literalism. |
| message | mensaje | Use for email content shown to a reader. |
| subject | asunto | Email field label. |
| send | enviar | Ensure button context makes the consequence clear. |
| sent | enviado | Match grammatical gender to the noun. |
| waiting | pendiente / en espera | Use *pendiente* for an item awaiting action. |
| receipt / evidence record | comprobante | Use for a saved record; clarify what it shows. |
| mailing receipt | comprobante de envío postal | Use for the receipt from mailing a letter. Do not confuse it with an email receipt or a broker's response. |
| call note | nota sobre la llamada | Optional note the person writes after a phone call. Avoid wording that suggests Free My ID records the call. |
| screenshot | captura de pantalla | Common, clear term. |
| status | estado | For progress/status; distinguish from a U.S. state field by context. |
| confirmed | confirmado | Match the noun's gender and number. |
| not found | no encontrado | Match the noun's gender and number. |
| reappeared | volvió a aparecer | Plain, readable phrase. |
| check | revisar | Use for a review/check action; *verificar* is more formal. |
| automatic | automático | Match gender/number; explain schedule in plain language. |
| schedule | programación | For the timing of recurring tasks; avoid technical jargon. |
| task | tarea | Common term for a step the reader needs to do. |
| step | paso | Use for instructions and process steps. |
| checklist | lista de pasos | Clearer than a borrowed technical term. |
| button | botón | Standard UI term. |
| link | enlace | Prefer over regional alternatives in cross-country Spanish. |
| label | etiqueta | For a field or accessible name; “texto del campo” may be clearer to readers. |
| field | campo | Familiar form term. |
| screen | pantalla | Standard UI term. |
| settings | configuración | Use as a navigation label; keep consistent with “setup.” |
| dark mode | modo oscuro | Common interface term. |
| error | error | Pair with a clear next step; avoid blame. |
| try again | volver a intentar | Courteous instruction; *Inténtelo de nuevo* is also usted-form. |
| back | volver | For navigation; *Atrás* is a concise button label. |
| next | siguiente | Concise button label. |
| save changes | guardar los cambios | Direct and familiar. |
| report | informe | Use for a downloadable summary. |
| result | resultado | Plain term. |
| score | puntuación | Explain scale and meaning wherever shown. |
| lower is better | cuanto menor, mejor | Short explanatory phrase. |
| on this computer | en esta computadora | Common Latin-American wording; use consistently. |
| cloud | nube | In privacy copy, clarify “servicio en la nube” if needed. |
| background | en segundo plano | Explain what runs automatically in nearby plain language. |
| automatic check | revisión automática | Clearer than a technical “escaneo.” |
| stop / turn off | desactivar | Use for a setting; *detener* for an action currently running. |
| turn on | activar | Use for settings and features. |
| close the app | cerrar la aplicación | Do not translate as uninstall. |
| uninstall | desinstalar | Standard software term; may need a brief explanation for some readers. |
| one site only | solo en ese sitio | Preserve the limited scope; do not imply internet-wide removal. |
| recheck | volver a revisar | Plain wording for another check. |
| user | persona usuaria | Inclusive, neutral wording; where space is tight, address the reader directly with usted. |
| you (formal) | usted | Use courteous usted forms; avoid switching to *tú*. |
| please | por favor | Use sparingly; direct instructions can remain courteous without repetition. |
