import React, { Component, MouseEvent } from "react";
import { ReactComponent as Lemon } from "./image/lemon.svg";

const HEIGHT = 214;
const MULTIPLIER = 3;

type AlbumMetadata = {
  album: string;
  color: string;
  image: string;
};

type FlourishEntry = {
  start: string;
  end: string;
  albums: Array<string>;
  weeks: bigint;
};

type TopChangesProps = {
  metadata: Map<string, AlbumMetadata>;
  flourish: Map<string, FlourishEntry>;
  dates: Array<string>;
};

type TopChangesState = {
  elements?: Array<JSX.Element>;
  selected?: bigint;
  width?: bigint;
  years?: Array<JSX.Element>;
};

export class TopChanges extends Component<TopChangesProps, TopChangesState> {
  constructor(props: TopChangesProps) {
    super(props);

    this.state = {};
  }

  componentDidMount = () => {
    this.generateInfographicElements();
  };

  render = (): JSX.Element => {
    if (this.state.width === undefined) {
      return <div>Loading infographic...</div>;
    }
    return (
      <div className="infographic">
        <div className="info-title">
          <Lemon className="lemon"/>
          <span className="heading">ALL-TIME ALBUMS</span>
          <span className="years">{this.state.years}</span>
        </div>

        <div className="scroller" id="scroller">
          <svg
            id="svg"
            width={String(this.state.width * 3n)}
            height={String(HEIGHT * MULTIPLIER)}
            viewBox={"0 0 " + this.state.width + " " + HEIGHT}
          >
            {this.state.elements}
          </svg>
        </div>
      </div>
    );
  };

  onYearClick: (
    offset: bigint
  ) => (_evt: MouseEvent<HTMLButtonElement>) => void = (offset) => {
    return (_evt) => {
      // console.log(`${year} ${offset}`);

      const scroller = document.getElementById("scroller");
      if (scroller === null) {
        throw new Error("scroller doesn't exist, shouldn't happen");
      }
      scroller.scrollLeft = Number(offset) * MULTIPLIER;
    };
  };

  generateInfographicElements = (): void => {
    const elements: Array<JSX.Element> = [];
    const years: Array<JSX.Element> = [];

    let xOffset: bigint = 0n;
    let column: bigint = 0n;
    let album: string;
    let albuminfo: AlbumMetadata;
    let information: FlourishEntry;
    let prevYear = 0n;

    while (Number(column) < this.props.dates.length) {
      const hold: FlourishEntry | undefined = this.props.flourish.get(
        this.props.dates[Number(column)]
      );
      if (hold === undefined) {
        throw new Error("undefined hold, shoudldn't happen.");
      } else {
        information = hold;
      }
      for (let i = 0; i < 10; i++) {
        album = information.albums[i];
        const albuminformation: AlbumMetadata | undefined =
          this.props.metadata.get(album);
        if (albuminformation === undefined) {
          throw new Error("undefined album information, shouldn't happen");
        }
        albuminfo = albuminformation;

        elements.push(
          <image
            href={"/levboard/albums/" + String(albuminfo.image)}
            width="16"
            height="16"
            x={String(xOffset)}
            y={String(i * 20 + 8)}
            key={album + "-" + column}
          />
        );
        let barOffset: bigint = 1n;
        while (barOffset < information.weeks) {
          elements.push(
            <rect
              width="1"
              height="16"
              x={String(xOffset + 15n + barOffset * 2n)}
              y={String(i * 20 + 8)}
              fill={"#" + albuminfo.color}
              key={album + "-" + column + "-" + barOffset}
            />
          );
          barOffset += 1n;
        }
      }

      // process year tags
      const year = BigInt(information.start.split("-")[0]);

      if (prevYear != year) {
        years.push(
          <button
            className="year-select rounded-button"
            id={"year-select-" + String(year)}
            onClick={this.onYearClick(xOffset)}
          >
            {String(year)}
          </button>
        );
        prevYear = year;
      }

      let header: string;

      // we gotta do this becasue ISO format does YYYY-MM-DD ("02-08",) which we
      // would much rather have as "2.8"
      // console.log(information.start, information.end);
      const start_month = Number(information.start.split("-")[1]).toString();
      const start_day = Number(information.start.split("-")[2]).toString();
      const end_month = Number(information.end.split("-")[1]).toString();
      const end_day = Number(information.end.split("-")[2]).toString();

      const start = start_month + "." + start_day;
      const end = end_month + "." + end_day;

      // console.log(start, end);

      if (information.weeks == 1n) {
        header = start;
      } else {
        header = start + " - " + end;
      }

      // add header text
      elements.push(
        <text
          x={String(xOffset + 7n + BigInt(information.weeks))}
          y="4"
          className="label"
          key={"top-label-" + column}
        >
          {header}
        </text>,
        <text
          x={String(xOffset + 7n + BigInt(information.weeks))}
          y="210"
          className="label"
          key={"bottom-label-" + column}
        >
          {header}
        </text>
      );

      // console.log("column " + column + " finished.");
      xOffset += 18n + 2n * BigInt(information.weeks);
      column += 1n;
    }

    this.setState({
      width: xOffset,
      elements: elements,
      years: years,
    });
  };
}
