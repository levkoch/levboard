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

type TopPackedProps = {
  metadata: Map<string, AlbumMetadata>;
  flourish: Map<string, FlourishEntry>;
  dates: Array<string>;
};

type TopPackedState = {
  flourish: Array<FlourishEntry>;
  dates: Array<string>;
  elements?: Array<JSX.Element>;
  selected: bigint;
  width?: bigint;
};

export class TopPacked extends Component<TopPackedProps, TopPackedState> {
  constructor(props: TopPackedProps) {
    super(props);

    const info = this.processEntries();

    this.state = { flourish: info.flourish, dates: info.dates, selected: 0n };
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
          <Lemon className="lemon" />
          <span className="heading">ALL-TIME ALBUMS</span>
        </div>

        <svg
          id="svg"
          width={String(this.state.width * 3n)}
          height={String(HEIGHT * MULTIPLIER)}
          viewBox={"0 0 " + this.state.width + " " + HEIGHT}
        >
          {this.state.elements}
        </svg>
      </div>
    );
  };

  /*
   * reorganizes the entries so that they only have one week at a time.
   */
  processEntries = (): {
    flourish: Array<FlourishEntry>;
    dates: Array<string>;
  } => {
    const newFlourish = new Array<FlourishEntry>();
    const newDates = new Array<string>();

    let column: bigint = 0n;
    let information: FlourishEntry;
    let currentDate: Date;

    while (Number(column) < this.props.dates.length) {
      const hold: FlourishEntry | undefined = this.props.flourish.get(
        this.props.dates[Number(column)]
      );
      if (hold === undefined) {
        throw new Error("undefined hold, shoudldn't happen.");
      } else {
        information = hold;
      }

      currentDate = new Date(information.start);

      for (let i = 0; i < information.weeks; i++) {
        newFlourish.push({
          start: currentDate.toISOString().split("T")[0],
          end: currentDate.toISOString().split("T")[0],
          albums: information.albums,
          weeks: 1n,
        });
        newDates.push(currentDate.toISOString().split("T")[0]);
        currentDate.setDate(currentDate.getDate() + 7);
      }

      column += 1n;
    }

    return {
      flourish: newFlourish,
      dates: newDates,
    };
  };


  onSetSelected: (week: bigint) => (_evt: MouseEvent) => void = (week) => {
    return (_evt: MouseEvent) => {
      if (week < 0n || week >= BigInt(this.state.flourish.length)) {
        throw Error("index out of bounds for weeks");
      }
      this.setState({ selected: week }, () => {
        // Regenerate elements after state update to reflect new selection
        this.generateInfographicElements();
      });
    };
  };

  generateInfographicElements = (): void => {
    const elements: Array<JSX.Element> = [];

    let xOffset: bigint = 0n;
    let column: bigint = 0n;
    let album: string;
    let albuminfo: AlbumMetadata;
    let information: FlourishEntry;

    while (Number(column) < this.state.dates.length) {
      const hold: FlourishEntry | undefined =
        this.state.flourish[Number(column)];
      if (hold === undefined) {
        throw new Error("undefined hold, shoudldn't happen.");
      } else {
        information = hold;
      }

      console.log(information);

      for (let i = 0; i < 10; i++) {
        album = information.albums[i];
        const albuminformation: AlbumMetadata | undefined =
          this.props.metadata.get(album);
        if (albuminformation === undefined) {
          throw new Error("undefined album information, shouldn't happen");
        }
        albuminfo = albuminformation;

        if (column === this.state.selected) {
          elements.push(
            <image
              href={"/levboard/albums/" + String(albuminfo.image)}
              width="16"
              height="16"
              x={String(xOffset)}
              y={String(i * 20 + 8)}
              key={"2-" + album + "-" + column}
            />
          );
        } else {
          elements.push(
            <rect
              width="1"
              height="16"
              x={String(xOffset)}
              y={String(i * 20 + 8)}
              fill={"#" + albuminfo.color}
              key={"2-" + album + "-" + column}
              onMouseOver={this.onSetSelected(column)}
            />
          );
        }
      }

      // Only display header text for the selected week
      if (column === this.state.selected) {
        // we gotta do this becasue ISO format does YYYY-MM-DD ("02-08",) which we
        // would much rather have as "2.8"
        console.log(information.start, information.end);
        const start_year = Number(information.start.split("-")[0]).toString();
        const start_month = Number(information.start.split("-")[1]).toString();
        const start_day = Number(information.start.split("-")[2]).toString();

        const start = start_month + "." + start_day + "." + start_year;

        // add header text only for selected week
        elements.push(
          <text
            x={String(xOffset + 7n + BigInt(information.weeks))}
            y="4"
            className="label"
            key={"top-label-" + column}
          >
            {start}
          </text>,
          <text
            x={String(xOffset + 7n + BigInt(information.weeks))}
            y="210"
            className="label"
            key={"bottom-label-" + column}
          >
            {start}
          </text>
        );
      }

      console.log("column " + column + " finished.");
      if (column === this.state.selected) {
        xOffset += 17n;
      } else {
        xOffset += 2n;
      }
      column += 1n;
    }
    console.log(elements);

    this.setState({
      width: xOffset,
      elements: elements,
    });
  };
}