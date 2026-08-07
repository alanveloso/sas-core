| método | endpoint | request schema | response schema | estado alterado | uut | consumidores |
|---|---|---|---|---|---|---|
| `BlacklistByFccId` | `/admin/injectdata/blacklist_fcc_id` | A dictionary with a single key-value pair where the key is "fccId" and the value | empty_200 | persist injection (injectdata/blacklist_ | implemented | GRA,HBT,REG,SIQ |
| `BlacklistByFccIdAndSerialNumber` | `/admin/injectdata/blacklist_fcc_id_and_serial_number` | A dictionary with the following key-value pairs: "fccId": (string) blacklisted F | empty_200 | persist injection (injectdata/blacklist_ | implemented | — |
| `GetDailyActivitiesStatus` | `/admin/get_daily_activities_status` | (none) | {completed: bool} | read-only status/query | implemented | EXZ,FAD,FDB,FPR,GPR,GRA,HBT,HELPER,IPR,MCP,PPR,SIQ,WDB |
| `GetPpaCreationStatus` | `/admin/get_ppa_status` | (none) | {completed: bool, withError: bool} | read-only status/query | implemented | HELPER,PCR,WDB |
| `InjectClusterList` | `/admin/injectdata/cluster_list` | (unspecified) | empty_200 | persist injection (injectdata/cluster_li | implemented | — |
| `InjectCpiUser` | `/admin/injectdata/cpi_user` | A dictionary with the following key-value pairs: "cpiId": (string) valid cpiId t | empty_200 | persist injection (injectdata/cpi_user) | implemented | REG |
| `InjectDatabaseUrl` | `/admin/injectdata/database_url` | Contains database url to be injected. | empty_200 | persist injection (injectdata/database_u | implemented | FDB,IPR,WDB |
| `InjectEscSensorDataRecord` | `/admin/injectdata/esc_sensor` | A dictionary with a single key-value pair where the key is "record" and the valu | empty_200 | persist injection (injectdata/esc_sensor | implemented | FAD,MCP |
| `InjectEscZone` | `/admin/injectdata/esc_zone` | (unspecified) | JSON body | persist injection (injectdata/esc_zone) | implemented | — |
| `InjectExclusionZone` | `/admin/injectdata/exclusion_zone` | A dictionary with the following key-value pairs: "zone": A GeoJSON object defini | JSON body | persist injection (injectdata/exclusion_ | implemented | EXZ |
| `InjectFccId` | `/admin/injectdata/fcc_id` | A dictionary with the following key-value pairs: "fccId": (string) valid fccId t | empty_200 | persist injection (injectdata/fcc_id) | implemented | BPR,DRG,EXZ,FAD,GRA,HBT,HELPER,HELPER.assertRegistered,MES,QPR,REG,RLQ,SCS,SDS,SIQ,WDB |
| `InjectFss` | `/admin/injectdata/fss` | A dictionary with a single key-value pair where the key is "record" and the valu | empty_200 | persist injection (injectdata/fss) | implemented | FPR,HBT,MCP,SIQ |
| `InjectPalDatabaseRecord` | `/admin/injectdata/pal_database_record` | For the contents of this request, please refer to the PAL Database TS (WINNF-16- | empty_200 | persist injection (injectdata/pal_databa | implemented | FAD,GRA,MCP,PCR,PPR,SIQ |
| `InjectPeerSas` | `/admin/injectdata/peer_sas` | A dictionary with the following key-value pairs: "certificateHash": the sha1 fin | empty_200 | persist injection (injectdata/peer_sas) | implemented | FAD,GRA,IPR,MCP,PCR,PPR,SSS |
| `InjectSasAdministratorRecord` | `/admin/injectdata/sas_admin` | A dictionary with a single key-value pair where the key is "record" and the valu | empty_200 | persist injection (injectdata/sas_admin) | implemented | — |
| `InjectUserId` | `/admin/injectdata/user_id` | A dictionary with a single key-value pair where the key is "userId" and the valu | empty_200 | persist injection (injectdata/user_id) | implemented | BPR,DRG,FAD,GRA,HBT,HELPER,HELPER.assertRegistered,MES,QPR,REG,RLQ,SCS,SDS,SIQ,WDB |
| `InjectWisp` | `/admin/injectdata/wisp` | A dictionary with two key-value pairs where the keys are "record" and "zone" wit | empty_200 | persist injection (injectdata/wisp) | implemented | FPR,GPR,HBT,MCP,SIQ |
| `InjectZoneData` | `/admin/injectdata/zone` | A dictionary with a single key-value pair where the key is "record" and the valu | zone id JSON | persist injection (injectdata/zone) | implemented | FAD,GRA,MCP,PCR,SIQ |
| `PreloadRegistrationData` | `/admin/injectdata/conditional_registration` | A dictionary with a single key-value pair where the key is "registrationData" an | empty_200 | persist injection (injectdata/conditiona | implemented | BPR,EXZ,FAD,GRA,HELPER,HELPER.assertRegistered,QPR,REG |
| `QueryPropagationAndAntennaModel` | `/admin/query/propagation_and_antenna_model` | A dictionary with multiple key-value pairs where the keys are reliabilityLevel:  | 501 Not Implemented | read-only status/query | unimplemented | PAT |
| `Reset` | `/admin/reset` | (none) | empty_200 | full UUT baseline reset | implemented | BPR,DRG,EPR,EXZ,FAD,FDB,FPR,GPR,GRA,HBT,HELPER,IPR,MCP,MES,PAT,PPR,QPR,REG,RLQ,SIQ,WDB |
| `ResetEscZone` | `/admin/trigger/esc_reset` | (unspecified) | empty_200 | trigger/esc_reset | implemented | — |
| `TriggerBulkDpaActivation` | `/admin/trigger/bulk_dpa_activation` | A dictionary with the following key-value pairs: "activate": (boolean) if True,  | empty_200 | trigger side-effect (trigger/bulk_dpa_ac | implemented | GRA,HBT,IPR,MCP,SIQ |
| `TriggerDailyActivitiesImmediately` | `/admin/trigger/daily_activities_immediately` | (none) | empty_200 | trigger side-effect (trigger/daily_activ | implemented | EXZ,FAD,FDB,FPR,GPR,GRA,HBT,HELPER,IPR,MCP,PPR,SIQ,WDB |
| `TriggerDpaActivation` | `/admin/trigger/dpa_activation` | A dictionary with the following key-value pairs: "dpaId": (string) it represents | empty_200 | trigger side-effect (trigger/dpa_activat | implemented | GRA,HBT,IPR,MCP,SIQ |
| `TriggerDpaDeactivation` | `/admin/trigger/dpa_deactivation` | A dictionary with the following key-value pairs: "dpaId": (string) it represents | empty_200 | trigger side-effect (trigger/dpa_deactiv | implemented | MCP |
| `TriggerEnableNtiaExclusionZones` | `/admin/trigger/enable_ntia_15_517` | (none) | empty_200 | trigger side-effect (trigger/enable_ntia | implemented | EXZ |
| `TriggerEnableScheduledDailyActivities` | `/admin/trigger/enable_scheduled_daily_activities` | (none) | empty_200 | trigger side-effect (trigger/enable_sche | implemented | FDB |
| `TriggerEscDisconnect` | `/admin/trigger/disconnect_esc` | (none) | empty_200 | trigger side-effect (trigger/disconnect_ | implemented | IPR |
| `TriggerEscZone` | `/admin/trigger/esc_detection` | (unspecified) | empty_200 | trigger side-effect (trigger/esc_detecti | implemented | — |
| `TriggerFullActivityDump` | `/admin/trigger/create_full_activity_dump` | (none) | empty_200 | trigger side-effect (trigger/create_full | implemented | FAD,HELPER,SSS |
| `TriggerLoadDpas` | `/admin/trigger/load_dpas` | (none) | empty_200 | trigger side-effect (trigger/load_dpas) | implemented | GRA,HBT,IPR,MCP,SIQ |
| `TriggerMeasurementReportHeartbeat` | `/admin/trigger/meas_report_in_heartbeat_response` | (none) | empty_200 | trigger side-effect (trigger/meas_report | implemented | MES |
| `TriggerMeasurementReportRegistration` | `/admin/trigger/meas_report_in_registration_response` | (none) | empty_200 | trigger side-effect (trigger/meas_report | implemented | MES |
| `TriggerPpaCreation` | `/admin/trigger/create_ppa` | A dictionary with multiple key-value pairs where the keys are cbsdIds: array of  | ppa_id string \| empty | trigger side-effect (trigger/create_ppa) | implemented | HELPER,PCR,WDB |
